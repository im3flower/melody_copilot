import React, { useEffect, useState } from "react";
import "./App.css";
import { MelodyUnit, Mood, Note, Chord, DefaultSeed } from "./types";
import {
  completeMelody,
  CompletionRequest,
  fetchDefaultSeed,
  fetchBridgeLatest,
  startLiveCapture,
  BridgeLatestResponse,
  notifyMax,
  exportMidi,
} from "./services/api";

const DEFAULT_NOTE_TEXT = [
  "C4 0 1",
  "D4 1 1",
  "E4 2 1",
  "F4 3 1",
].join("\n");

const DEFAULT_CHORDS: Chord[] = [
  { symbol: "Am", start: 0, duration: 4 },
  { symbol: "F", start: 4, duration: 4 },
  { symbol: "C", start: 8, duration: 4 },
  { symbol: "G", start: 12, duration: 4 },
];

const UNIT_OPTIONS: MelodyUnit[] = ["bar", "step", "ms"];

const parseNotesInput = (raw: string): Note[] => {
  const lines = raw
    .split(/\n+/)
    .map(line => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    throw new Error("请输入至少一行音符，例如 C4 0 1");
  }

  return lines.map((line, index) => {
    const parts = line.split(/\s+/);
    if (parts.length !== 3) {
      throw new Error(`第 ${index + 1} 行格式需要为 'PITCH START DURATION'`);
    }
    const [pitch, startText, durationText] = parts;
    const start = Number(startText);
    const duration = Number(durationText);
    if (Number.isNaN(start) || Number.isNaN(duration)) {
      throw new Error(`第 ${index + 1} 行的时间必须是数字`);
    }
    if (duration <= 0) {
      throw new Error(`第 ${index + 1} 行的时值需要大于 0`);
    }
    return {
      pitch: pitch.toUpperCase(),
      start,
      duration,
    };
  });
};

const App: React.FC = () => {
  const [notesInput, setNotesInput] = useState<string>(DEFAULT_NOTE_TEXT);
  const [defaultNotesText, setDefaultNotesText] = useState<string>(DEFAULT_NOTE_TEXT);
  const [mood, setMood] = useState<string>(Mood.HAPPY);
  const [bpm, setBpm] = useState<number>(120);
  const [defaultBpm, setDefaultBpm] = useState<number>(120);
  const [chords, setChords] = useState<Chord[]>(DEFAULT_CHORDS);
  const [defaultChords, setDefaultChords] = useState<Chord[]>(DEFAULT_CHORDS);
  const [chordsInput, setChordsInput] = useState<string>(
    DEFAULT_CHORDS.map(c => `${c.symbol} ${c.start} ${c.duration}`).join("\n")
  );
  const [lengthValue, setLengthValue] = useState<number>(4);
  const [lengthUnit, setLengthUnit] = useState<MelodyUnit>("bar");
  const [adventureness, setAdventureness] = useState<number>(35);

  const [loading, setLoading] = useState(false);
  const [seedLoading, setSeedLoading] = useState(true);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [requestDuration, setRequestDuration] = useState<number | null>(null);
  const [addedNotes, setAddedNotes] = useState<Note[]>([]);
  const [lastPayload, setLastPayload] = useState<CompletionRequest | null>(null);
  
  const [capturingFromLive, setCapturingFromLive] = useState(false);
  const [captureTimeout, setCaptureTimeout] = useState<NodeJS.Timeout | null>(null);
  const [capturingChordsFromLive, setCapturingChordsFromLive] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let active = true;

    const loadDefault = async () => {
      try {
        setSeedLoading(true);
        const seed: DefaultSeed = await fetchDefaultSeed();
        if (!active) return;
        const text = seed.notes_text?.trim()
          ? seed.notes_text.trim()
          : seed.notes.map(n => `${n.pitch} ${n.start} ${n.duration}`).join("\n");
        setDefaultNotesText(text);
        setNotesInput(text);
        const bpmValue = Number.isFinite(seed.bpm) ? Number(seed.bpm) : 120;
        setDefaultBpm(bpmValue);
        setBpm(bpmValue);
        if (seed.chords?.length) {
          setDefaultChords(seed.chords);
          setChords(seed.chords);
        }
        setStatus("已载入默认 MIDI 示例");
      } catch (err) {
        if (!active) return;
        console.error("Failed to load default seed", err);
        setStatus("无法加载默认示例，使用内置音符");
      } finally {
        if (active) {
          setSeedLoading(false);
        }
      }
    };

    loadDefault();
    return () => {
          active = false;
    };
  }, []);

  // Cleanup: cancel polling on unmount
  useEffect(() => {
    return () => {
      if (captureTimeout) {
        clearTimeout(captureTimeout);
      }
    };
  }, [captureTimeout]);

  const handleReset = () => {
    setNotesInput(defaultNotesText);
    setBpm(defaultBpm);
    setChords(defaultChords);
    setChordsInput(defaultChords.map(c => `${c.symbol} ${c.start} ${c.duration}`).join("\n"));
    setStatus("");
    setError(null);
    setAddedNotes([]);
    setLastPayload(null);
    setRequestDuration(null);
    if (captureTimeout) clearTimeout(captureTimeout);
    setCapturingFromLive(false);
  };

  const parseChordsInput = (raw: string): Chord[] => {
    const lines = raw
      .split(/\n+/)
      .map(line => line.trim())
      .filter(Boolean);

    // 允许为空：用户可清空和弦，表示不使用和弦约束
    if (!lines.length) {
      return [];
    }

    return lines.map((line, index) => {
      const parts = line.split(/\s+/);
      if (parts.length !== 3) {
        throw new Error(`第 ${index + 1} 行格式需要为 'SYMBOL START DURATION'`);
      }
      const [symbol, startText, durationText] = parts;
      const start = Number(startText);
      const duration = Number(durationText);
      if (Number.isNaN(start) || Number.isNaN(duration)) {
        throw new Error(`第 ${index + 1} 行的时间必须是数字`);
      }
      if (duration <= 0) {
        throw new Error(`第 ${index + 1} 行的时值需要大于 0`);
      }
      return { symbol, start, duration };
    });
  };

  const handleComplete = async () => {
    setLoading(true);
    setError(null);
    setStatus("正在准备请求…");
    setRequestDuration(null);

    let parsedNotes: Note[] = [];
    try {
      parsedNotes = parseNotesInput(notesInput);
    } catch (parseErr) {
      setLoading(false);
      setError(parseErr instanceof Error ? parseErr.message : String(parseErr));
      setStatus("");
      return;
    }

    // 和弦逻辑与旋律相同：按输入框即时解析，无需单独“应用”按钮
    let parsedChords: Chord[] = [];
    try {
      parsedChords = parseChordsInput(chordsInput);
      setChords(parsedChords);
    } catch (err) {
      setLoading(false);
      setError(err instanceof Error ? err.message : String(err));
      setStatus("");
      return;
    }

    const payload: CompletionRequest = {
      original_notes: parsedNotes,
      mood: mood.trim() || Mood.HAPPY,
      bpm,
      length_value: lengthValue,
      length_unit: lengthUnit,
      adventureness,
      chords: parsedChords,
    };

    setLastPayload(payload);

    const start = performance.now();
    try {
      const response = await completeMelody(payload);
      setAddedNotes(response.added_notes);
      setNotesInput(
        response.full_track
          .map(n => `${n.pitch} ${n.start} ${n.duration}`)
          .join("\n")
      );
      setStatus(
        response.added_notes.length
          ? `成功添加 ${response.added_notes.length} 个音符`
          : "后端返回了相同的音符"
      );
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message || "Failed to fetch"
          : "Failed to fetch"
      );
      setStatus("");
    } finally {
      setRequestDuration(performance.now() - start);
      setLoading(false);
    }
  };

  const handleExportMidi = async () => {
    setExporting(true);
    setError(null);
    setStatus("正在导出 MIDI…");

    let parsedNotes: Note[] = [];
    try {
      parsedNotes = parseNotesInput(notesInput);
    } catch (parseErr) {
      setExporting(false);
      setError(parseErr instanceof Error ? parseErr.message : String(parseErr));
      setStatus("");
      return;
    }

    try {
      const res = await exportMidi({ notes: parsedNotes, bpm });
      setStatus(`已导出 MIDI: ${res.path}`);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setExporting(false);
    }
  };

  const handleLoadFromLive = async () => {
    setCapturingFromLive(true);
    setError(null);
    setStatus("⏳ 已准备好，请在 Max for Live 中点击「捕获」按钮...");
    
    // 通知后端开始监听
    try {
      await startLiveCapture();
    } catch (err) {
      console.error("Failed to start capture", err);
      setError("无法启动监听");
      setCapturingFromLive(false);
      setStatus("");
      return;
    }

    // 顺便推一条消息给 Max（默认发到 7401，经由后端）
    notifyMax({
      event: "start_capture",
      data: {
        hint: "frontend-button",
        bpm,
        mood,
        length_value: lengthValue,
        length_unit: lengthUnit,
      },
    }).catch(err => {
      console.error("Notify Max failed", err);
      // 不阻塞主流程，仅提示状态
      setStatus(prev => prev || "监听中 (Max 未确认)");
    });

    // 轮询查询结果（最多 8 秒，每 1 秒查询一次）
    let attempts = 0;
    const maxAttempts = 8;
    
    const pollResult = async () => {
      if (attempts >= maxAttempts) {
        setCapturingFromLive(false);
        setError("超时：未收到 Max for Live 的数据。请确认已在 Max 中点击捕获按钮");
        setStatus("");
        return;
      }

      try {
        const result: BridgeLatestResponse = await fetchBridgeLatest();
        if (result.has_data) {
          // 收到数据
          setNotesInput(
            result.full_track
              .map(n => `${n.pitch} ${n.start} ${n.duration}`)
              .join("\n")
          );
          setAddedNotes(result.added_notes);
          setStatus(`✓ 成功从 Live 加载 ${result.full_track.length} 个音符`);
          setCapturingFromLive(false);
          return;
        }
      } catch (err) {
        console.error("Poll error", err);
      }

      attempts++;
      const remainingTime = (maxAttempts - attempts);
      setStatus(`⏳ 等待中... (${remainingTime}s)`);
      
      const timeout = setTimeout(pollResult, 1000);
      setCaptureTimeout(timeout);
    };

    pollResult();
  };

  // 和弦版：同样从 Live 捕获，但结果写入和弦输入框
  const handleLoadChordsFromLive = async () => {
    setCapturingChordsFromLive(true);
    setError(null);
    setStatus("⏳ 已准备好，请在 Max for Live 中点击「捕获」按钮（和弦）...");

    try {
      await startLiveCapture();
    } catch (err) {
      console.error("Failed to start capture", err);
      setError("无法启动监听");
      setCapturingChordsFromLive(false);
      setStatus("");
      return;
    }

    notifyMax({
      event: "start_capture",
      data: {
        hint: "frontend-button-chords",
        bpm,
        mood,
        length_value: lengthValue,
        length_unit: lengthUnit,
      },
    }).catch(err => {
      console.error("Notify Max failed", err);
      setStatus(prev => prev || "监听中 (Max 未确认)");
    });

    let attempts = 0;
    const maxAttempts = 8;

    const pollResult = async () => {
      if (attempts >= maxAttempts) {
        setCapturingChordsFromLive(false);
        setError("超时：未收到 Max for Live 的数据。请确认已在 Max 中点击捕获按钮");
        setStatus("");
        return;
      }

      try {
        const result: BridgeLatestResponse = await fetchBridgeLatest();
        if (result.has_data) {
          const text = result.full_track
            .map(n => `${n.pitch} ${n.start} ${n.duration}`)
            .join("\n");
          setChordsInput(text);
          setChords(parseChordsInput(text));
          setStatus(`✓ 成功从 Live 加载和弦（共 ${result.full_track.length} 行）`);
          setCapturingChordsFromLive(false);
          return;
        }
      } catch (err) {
        console.error("Poll error", err);
      }

      attempts++;
      const remainingTime = maxAttempts - attempts;
      setStatus(`⏳ 等待中... (${remainingTime}s)`);

      const timeout = setTimeout(pollResult, 1000);
      setCaptureTimeout(timeout);
    };

    pollResult();
  };

  return (
    <div className="app-shell compact">
      <main className="card card--solo">
        <header className="solo-header">
          <div>
            <p className="eyebrow">Melody Copilot</p>
            <h1>继续你的旋律</h1>
            <p className="lede">
              贴上起始音符（格式：PITCH START DURATION），填写参数后点击
              Complete 即可调用后端。
            </p>
          </div>
          <button className="ghost-button" onClick={handleReset}>
            重置示例
          </button>
        </header>

        <section className="form-block">
          <div className="panel-grid">
            <div className="panel panel--notes">
              <label className="stack">
                <span>Seed Notes</span>
                <textarea
                  className="notes-input"
                  value={notesInput}
                  onChange={e => setNotesInput(e.target.value)}
                  spellCheck={false}
                />
                <small>示例：C4 0 1（音高 起始 拍长，使用 quarterLength）</small>
              </label>
            </div>

            <div className="panel panel--chords">
              <label className="stack">
                <span>Chords (符号 起始 拍长)</span>
                <textarea
                  className="notes-input"
                  value={chordsInput}
                  onChange={e => setChordsInput(e.target.value)}
                  spellCheck={false}
                  placeholder="Am 0 4\nF 4 4\nC 8 4\nG 12 4"
                />
                <small>示例：Am 0 4（和弦 起始 拍长，格式与旋律行一致）</small>
                <div className="actions chords">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      const text = defaultChords.map(c => `${c.symbol} ${c.start} ${c.duration}`).join("\n");
                      setChordsInput(text);
                      setChords(defaultChords);
                      setStatus("已获取默认和弦");
                      setError(null);
                    }}
                  >
                    获取和弦
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={handleLoadChordsFromLive}
                    disabled={capturingChordsFromLive || loading}
                  >
                    {capturingChordsFromLive ? "📡 监听中…" : "📡 从 Live 加载和弦"}
                  </button>
                </div>
              </label>
            </div>

            <div className="panel panel--controls">
              <div className="settings-grid">
                <label>
                  <span>Mood</span>
                  <select value={mood} onChange={e => setMood(e.target.value)}>
                    {Object.values(Mood).map(option => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>BPM</span>
                  <input
                    type="number"
                    min={40}
                    max={220}
                    value={bpm}
                    onChange={e => setBpm(Number(e.target.value))}
                  />
                </label>

                <label>
                  <span>Length</span>
                  <input
                    type="number"
                    step="0.25"
                    value={lengthValue}
                    onChange={e => setLengthValue(Number(e.target.value))}
                  />
                </label>

                <label>
                  <span>Unit</span>
                  <select
                    value={lengthUnit}
                    onChange={e => setLengthUnit(e.target.value as MelodyUnit)}
                  >
                    {UNIT_OPTIONS.map(option => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="full">
                  <span>Adventureness ({adventureness}%)</span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={adventureness}
                    onChange={e => setAdventureness(Number(e.target.value))}
                  />
                </label>
              </div>

              <div className="actions single">
                <button
                  className="primary-button"
                  onClick={handleComplete}
                  disabled={loading}
                >
                  {loading ? "调用中…" : "Complete"}
                </button>
                <button
                  className="secondary-button"
                  onClick={handleLoadFromLive}
                  disabled={capturingFromLive || loading}
                  type="button"
                >
                  {capturingFromLive ? "📡 监听中…" : "📡 从 Live 加载旋律"}
                </button>
                <button
                  className="ghost-button"
                  onClick={handleExportMidi}
                  disabled={exporting || loading}
                  type="button"
                >
                  {exporting ? "导出中…" : "💾 导出 MIDI 并打开文件夹"}
                </button>
              </div>

              {error && <p className="alert alert--error">{error}</p>}
              {status && (
                <p className="alert alert--success">
                  {status}
                  {requestDuration && (
                    <span>{` (${requestDuration.toFixed(0)} ms)`}</span>
                  )}
                </p>
              )}
            </div>
          </div>

          {addedNotes.length > 0 && (
            <details className="added-list simple" open>
              <summary>最新生成 {addedNotes.length} 个音符</summary>
              <ul>
                {addedNotes.slice(0, 8).map((note, index) => (
                  <li key={`added-${index}`}>
                    <span>{note.pitch}</span>
                    <span>start {note.start}</span>
                    <span>len {note.duration}</span>
                  </li>
                ))}
                {addedNotes.length > 8 && (
                  <li className="faded">… 还有 {addedNotes.length - 8} 个</li>
                )}
              </ul>
            </details>
          )}

          {lastPayload && (
            <details className="request-preview compact" open>
              <summary>最近一次请求体</summary>
              <pre>{JSON.stringify(lastPayload, null, 2)}</pre>
            </details>
          )}

        </section>
      </main>
    </div>
  );
};

export default App;

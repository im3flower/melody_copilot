inlets = 1;
outlets = 1;

var acc = [];
var DEBUG = true;
var LOG_TO_FILE = false;
var LOG_PATH = "C:/Users/18200/Desktop/gen_ai/melody_copilot/notesender.log";
var REQUIRED_TAG = "mytag";

// 初始化状态
var initMsg = "dbg init notesender.js loaded (js object, no node/require support)";
post(initMsg + "\n");

function log(msg) {
  var line = "dbg " + msg;
  if (DEBUG) post(line + "\n");
}

// 手动测试日志写入：给 js 发送消息 logtest
function logtest() {
  post("dbg logtest (no file logging in js object)\n");
}

// bang 清空累积，防止跨批次串音符
function bang() {
  acc = [];
  log("reset acc");
  outlet(0, "reset");
}

// 处理 select_all_notes 消息
function select_all_notes() {
  var a = arrayfromargs(messagename, arguments);
  log("recv select_all_notes " + a.join(" "));
  // 只是控制命令，忽略
}

// 处理 get_selected_notes 消息
function get_selected_notes() {
  var a = arrayfromargs(messagename, arguments);
  log("recv get_selected_notes " + a.join(" "));
  processNotes(a);
}

// 处理 get_selected_notes_extended 消息（返回字典）
function get_selected_notes_extended() {
  var a = arrayfromargs(messagename, arguments);
  log("recv get_selected_notes_extended " + a.join(" "));
  // 字典格式需要特殊处理，暂时忽略或提示用户用旧 API
  post("warning: get_selected_notes_extended returns dictionary, use get_selected_notes instead\n");
}

// 处理带标签的音符数据
function mytag() {
  var a = arrayfromargs(messagename, arguments);
  log("recv mytag " + a.join(" "));
  processNotes(a);
}

function list() {
  var a = arrayfromargs(messagename, arguments);
  log("recv list " + a.join(" "));
  processNotes(a);
}

function anything() {
  var a = arrayfromargs(messagename, arguments);
  log("recv anything " + messagename + " " + a.join(" "));
  processNotes(a);
}

// 处理音符数据的核心逻辑
function processNotes(a) {
  // 检查终止符（支持带前缀的 "get_selected_notes done"）
  if (a.indexOf("done") !== -1 && a.length <= 2) {
    sendPayload();
    return;
  }
  
  // 如果含有前缀（如 get_selected_notes），找到第一个 "note" 再处理
  var noteIdx = a.indexOf("note");
  if (noteIdx !== -1) {
    a = a.slice(noteIdx + 1); // 去掉 "note"
  }

  // 跳过统计头（notes 8）
  if (a.length >= 2 && a[0] === "notes") {
    log("skip notes header " + a.join(" "));
    return;
  }

  // 提取所有数字，按 3 个一组（pitch/start/dur）
  var nums = [];
  for (var i = 0; i < a.length; i++) {
    var n = toNumber(a[i]);
    if (!isNaN(n)) nums.push(n);
  }

  for (var j = 0; j + 2 < nums.length; j += 3) {
    var p = nums[j];
    var start = nums[j + 1];
    var dur = nums[j + 2];
    acc.push({ pitch: toName(p), start: start, duration: dur });
  }

  if (!nums.length) {
    log("no numeric data, skip");
  }

  log("acc size " + acc.length);
}

function toNumber(x) {
  return typeof x === "number" ? x : parseFloat(x); 
}

function toName(p) {
  var names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
  var n = p % 12, oct = Math.floor(p / 12) - 1;
  return names[n] + oct;
}

function sendPayload() {
  if (!acc.length) {
    outlet(0, "err no_notes");
    log("no notes, skip send");
    return;
  }

  // Bridge + Backend expect keys: full_track, added_notes
  var payload = {
    full_track: acc,
    added_notes: [],
    bpm: 120,
    mood: "happy",
    length_value: 4,
    length_unit: "bar",
    adventureness: 35
  };

  acc = [];
  log("sending payload len=" + payload.full_track.length);
  log("payload json " + JSON.stringify(payload));

  // 直接输出 JSON 字符串，后面可接 [prepend send] → [udpsend 127.0.0.1 7400]
  // 不再加自定义前缀，避免被过滤
  outlet(0, JSON.stringify(payload));
}





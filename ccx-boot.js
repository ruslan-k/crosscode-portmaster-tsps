// quixjs boot for CrossCode: the globals of assets/node-webkit.html, a $
// stub for the jQuery calls the engine makes on the HTML shell, and the
// start call that html does on window.onload.

var IG_GAME_SCALE = 1, IG_GAME_CACHE = "", IG_ROOT = "", IG_WIDTH = 568, IG_HEIGHT = 320;
var IG_HIDE_DEBUG = false, IG_SCREEN_MODE_OVERRIDE = 2, IG_WEB_AUDIO_BGM = false;
var IG_FORCE_HTML5_AUDIO = false, LOAD_LEVEL_ON_GAME_START = null;
var IG_GAME_DEBUG = false, IG_GAME_BETA = false;

// the engine reads canvas.style.width as a CSS string ("1136px"); quixjs
// stores it as a number, and has no #game/#options elements at all
(function () {
  var gid = document.getElementById;
  document.getElementById = function (id) {
    var e = gid.call(document, id);
    if (!e) e = document.createElement("div");
    if (e.style) {
      if (typeof e.style.width === "number") e.style.width = e.style.width + "px";
      if (typeof e.style.height === "number") e.style.height = e.style.height + "px";
    }
    return e;
  };
})();

// the loader loads every json with $.ajax(dataType:"json"); XHR is the
// transport quixjs already implements
window.jQuery = window.$ = (function () {
  function noop_el() {
    var o = { css: function () { return o; }, attr: function () { return o; },
      addClass: function () { return o; }, removeClass: function () { return o; },
      show: function () { return o; }, hide: function () { return o; },
      append: function () { return o; }, html: function () { return o; },
      text: function () { return o; }, on: function () { return o; },
      width: function () { return 0; }, height: function () { return 0; } };
    return o;
  }
  var jq = function () { return noop_el(); };
  jq.ajax = function (o) {
    var x = new XMLHttpRequest();
    x.open(o.type || "GET", o.url, o.async !== false);
    if (o.responseType) x.responseType = o.responseType;
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var ok = (x.status >= 200 && x.status < 300) || x.status === 0;
      var data = x.responseText, err = null;
      if (ok && o.dataType === "json") {
        try { data = JSON.parse(data); } catch (e) { ok = false; err = "parsererror"; }
      }
      if (ok) { if (o.success) o.success.call(o.context || window, data, "success", x); }
      else if (o.error) o.error.call(o.context || window, x, err || "error", err || x.statusText);
    };
    x.send(o.data || null);
    return x;
  };
  jq.getJSON = function (url, cb) { return jq.ajax({ url: url, dataType: "json", success: cb }); };
  return jq;
})();

// impact.base.dom parses HTML with DOMParser; the game only uses ig.dom for
// small HTML overlays, so a document-shaped stub is enough
function DOMParser() {}
DOMParser.prototype.parseFromString = function (s, type) {
  var el = document.createElement("div");
  return { documentElement: el, body: el, getElementsByTagName: function () { return []; },
           querySelector: function () { return null; }, querySelectorAll: function () { return []; },
           createElement: function (t) { return document.createElement(t); } };
};

// browser globals the bundle and jQuery-era code expect
var name = "", status = "", closed = false;
var self = window, top = window, parent = window, frames = window;

// the engine reads process.versions['node-webkit'] to pick its nw.js paths
if (window.process && window.process.versions) {
  window.process.versions['node-webkit'] = '0.55.0';
  window.process.arch = 'x64';
}

(function wait() {
  if (window.startCrossCode) window.startCrossCode();
  else setTimeout(wait, 100);
})();

/**
 * AI-Agent Website Operator — embeddable chat widget
 *
 * Embed with one script tag:
 *   <script src="https://agent.example.com/widget.js"
 *     data-tenant="TENANT_ID"
 *     data-api="https://agent.example.com"
 *     data-color="#4f46e5"
 *     data-name="TechZone"
 *     data-position="bottom-right"></script>
 *
 * Vanilla JS, zero dependencies. All markup and styles live inside an
 * open Shadow DOM so the host site's CSS cannot leak in or out.
 *
 * ------------------------------------------------------------------
 * DEMO MOCK — screenshot use only, never in production
 * If the script tag carries data-mock="true", all network is skipped:
 *   - config comes from window.__aiAgentMock.config()
 *   - messages go through window.__aiAgentMock.chat({tenant_id, session_id,
 *     message, page_url, page_title}), which returns a Promise resolving
 *     to the same response shape as POST /api/chat.
 * ------------------------------------------------------------------
 */
(function () {
  'use strict';

  /* ---------------------------------------------------------------
   * 1. Read configuration from the script tag
   * ------------------------------------------------------------- */
  var scriptEl = document.currentScript;
  if (!scriptEl) {
    // Fallback: find the script tag by data-tenant attribute.
    var candidates = document.querySelectorAll('script[data-tenant]');
    scriptEl = candidates[candidates.length - 1] || null;
  }
  if (!scriptEl) return;

  var DATASET = scriptEl.dataset || {};

  // Resolve the script's own origin — used as the default API base.
  var scriptOrigin = null;
  try {
    scriptOrigin = new URL(scriptEl.src, window.location.href).origin;
  } catch (e) {
    scriptOrigin = window.location.origin;
  }

  // DEMO MOCK — screenshot use only, never in production.
  var MOCK_MODE = (DATASET.mock === 'true');

  var TENANT = DATASET.tenant || '';
  var API_BASE = (DATASET.api || scriptOrigin).replace(/\/+$/, '');
  var BRAND_COLOR = /^#[0-9a-fA-F]{3,8}$/.test(DATASET.color || '')
    ? DATASET.color
    : '#4f46e5';
  var POSITION = DATASET.position === 'bottom-left' ? 'bottom-left' : 'bottom-right';
  var NAME_OVERRIDE = (DATASET.name || '').trim();

  if (!TENANT) {
    if (window.console) console.warn('[ai-agent] widget: missing data-tenant, aborting.');
    return;
  }

  var SID_KEY = 'aiagent_sid_' + TENANT;
  var TRIGGER_KEY = 'aiagent_triggered_' + TENANT;

  function getSessionId() {
    try {
      var existing = window.sessionStorage.getItem(SID_KEY);
      if (existing) return existing;
      var sid = 's_' + Date.now().toString(36) + '_' +
        Math.random().toString(36).slice(2, 12);
      window.sessionStorage.setItem(SID_KEY, sid);
      return sid;
    } catch (e) {
      // sessionStorage unavailable (private mode) — ephemeral id.
      return 's_' + Date.now().toString(36) + '_' +
        Math.random().toString(36).slice(2, 12);
    }
  }

  var SESSION_ID = getSessionId();

  /* ---------------------------------------------------------------
   * 2. Minimal fallback CSS (used only if widget.css fails to load)
   * ------------------------------------------------------------- */
  var FALLBACK_CSS =
    '.aia-root{--brand:' + BRAND_COLOR + ';position:fixed;z-index:2147483647;' +
    (POSITION === 'bottom-left' ? 'left:20px;' : 'right:20px;') + 'bottom:20px;font-family:' +
    '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}' +
    '.aia-bubble{width:58px;height:58px;border-radius:50%;border:none;cursor:pointer;' +
    'background:var(--brand);color:#fff;display:flex;align-items:center;justify-content:center;' +
    'box-shadow:0 6px 20px rgba(0,0,0,.25);}' +
    '.aia-panel{width:min(380px,calc(100vw - 40px));height:min(560px,calc(100vh - 120px));' +
    'background:#fff;border-radius:16px;display:flex;flex-direction:column;overflow:hidden;' +
    'box-shadow:0 18px 60px rgba(0,0,0,.25);}' +
    '.aia-hidden{display:none !important;}';

  /* ---------------------------------------------------------------
   * 3. Shadow host + DOM skeleton
   * ------------------------------------------------------------- */
  var host = document.createElement('div');
  host.setAttribute('data-ai-agent-widget', TENANT);
  host.style.cssText = 'all:initial;';
  document.body.appendChild(host);

  var shadow = host.attachShadow({ mode: 'open' });

  var root = document.createElement('div');
  root.className = 'aia-root aia-' + POSITION;
  root.style.setProperty('--brand', BRAND_COLOR);
  shadow.appendChild(root);

  var SVG_CHAT =
    '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 ' +
    '8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 ' +
    '8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
    '</svg>';

  var SVG_CLOSE =
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" ' +
    'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true">' +
    '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' +
    '</svg>';

  var SVG_SEND =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">' +
    '<path d="M3.4 20.4l17.45-8.4L3.4 3.6l2.55 8.4 2.55 8.4zM6.9 12.5h6.9v2H6.9z"/>' +
    '</svg>';

  var SVG_GEAR =
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="3"/>' +
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 ' +
    '1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 ' +
    '9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 ' +
    '.33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 ' +
    '1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 ' +
    '1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 ' +
    '1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 ' +
    '1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>' +
    '</svg>';

  root.innerHTML =
    '<button class="aia-bubble" type="button" aria-label="Open chat" aria-expanded="false">' +
      '<span class="aia-bubble-ring" aria-hidden="true"></span>' +
      '<span class="aia-bubble-icon aia-icon-chat">' + SVG_CHAT + '</span>' +
      '<span class="aia-bubble-icon aia-icon-close aia-hidden">' + SVG_CLOSE + '</span>' +
    '</button>' +
    '<div class="aia-panel aia-panel-closed aia-hidden" role="dialog" aria-label="Chat">' +
      '<div class="aia-header">' +
        '<div class="aia-header-meta">' +
          '<span class="aia-online-dot" aria-hidden="true"></span>' +
          '<div class="aia-header-text">' +
            '<div class="aia-business-name"></div>' +
            '<div class="aia-business-status">Online · typically replies instantly</div>' +
          '</div>' +
        '</div>' +
        '<button class="aia-close" type="button" aria-label="Close chat">' + SVG_CLOSE + '</button>' +
      '</div>' +
      '<div class="aia-messages" aria-live="polite"></div>' +
      '<div class="aia-chips aia-hidden" aria-label="Quick replies"></div>' +
      '<div class="aia-typing aia-hidden" aria-hidden="true">' +
        '<span></span><span></span><span></span>' +
      '</div>' +
      '<form class="aia-input-row" autocomplete="off">' +
        '<input class="aia-input" type="text" name="message" ' +
          'placeholder="Ask about our products…" aria-label="Type your message" maxlength="1000"/>' +
        '<button class="aia-send" type="submit" aria-label="Send message">' + SVG_SEND + '</button>' +
      '</form>' +
    '</div>';

  /* ---------------------------------------------------------------
   * 4. Load widget.css relative to the script tag URL
   * ------------------------------------------------------------- */
  function injectStyle(cssText) {
    var style = document.createElement('style');
    style.textContent = cssText;
    shadow.insertBefore(style, root);
  }

  function cssUrl() {
    try {
      return new URL('widget.css', scriptEl.src).href;
    } catch (e) {
      return 'widget.css';
    }
  }

  if (window.fetch) {
    window.fetch(cssUrl(), { credentials: 'omit' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function (css) {
        injectStyle(css || FALLBACK_CSS);
      })
      .catch(function () {
        injectStyle(FALLBACK_CSS);
      });
  } else {
    injectStyle(FALLBACK_CSS);
  }

  /* ---------------------------------------------------------------
   * 5. Element handles
   * ------------------------------------------------------------- */
  var bubble = root.querySelector('.aia-bubble');
  var bubbleIconChat = root.querySelector('.aia-icon-chat');
  var bubbleIconClose = root.querySelector('.aia-icon-close');
  var panel = root.querySelector('.aia-panel');
  var headerName = root.querySelector('.aia-business-name');
  var messagesEl = root.querySelector('.aia-messages');
  var chipsEl = root.querySelector('.aia-chips');
  var typingEl = root.querySelector('.aia-typing');
  var formEl = root.querySelector('.aia-input-row');
  var inputEl = root.querySelector('.aia-input');
  var closeBtn = root.querySelector('.aia-close');
  var sendBtn = root.querySelector('.aia-send');

  var config = {
    business_name: NAME_OVERRIDE || 'Assistant',
    brand_color: BRAND_COLOR,
    welcome_message: 'Hi there! How can I help you today?',
    trigger: { enabled: false, pages: [], delay_sec: 25, message: '' }
  };

  headerName.textContent = config.business_name;

  /* ---------------------------------------------------------------
   * 6. Rendering helpers
   * ------------------------------------------------------------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function safeUrl(u) {
    try {
      var parsed = new URL(u, window.location.href);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return parsed.href;
    } catch (e) { /* invalid url */ }
    return null;
  }

  function addUserMessage(text) {
    var wrap = document.createElement('div');
    wrap.className = 'aia-msg aia-msg-user';
    var bubble = document.createElement('div');
    bubble.className = 'aia-bubble-text';
    bubble.textContent = text;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  function addBotMessage(data) {
    // data: { reply, sources, tools_used, suggested_replies }
    var wrap = document.createElement('div');
    wrap.className = 'aia-msg aia-msg-bot';

    // Tool-call cards render above the reply — signature visual.
    var tools = Array.isArray(data.tools_used) ? data.tools_used : [];
    tools.forEach(function (tool) {
      wrap.appendChild(buildToolCard(tool));
    });

    var reply = document.createElement('div');
    reply.className = 'aia-bubble-text';
    reply.textContent = data.reply || '';
    wrap.appendChild(reply);

    var sources = Array.isArray(data.sources) ? data.sources : [];
    if (sources.length) {
      wrap.appendChild(buildSources(sources));
    }

    messagesEl.appendChild(wrap);
    scrollToBottom();

    renderChips(data.suggested_replies);
  }

  function buildToolCard(tool) {
    var card = document.createElement('div');
    card.className = 'aia-tool-card';

    var icon = document.createElement('span');
    icon.className = 'aia-tool-icon';
    icon.innerHTML = SVG_GEAR;
    card.appendChild(icon);

    var body = document.createElement('div');
    body.className = 'aia-tool-body';

    var title = document.createElement('div');
    title.className = 'aia-tool-title';
    title.appendChild(document.createTextNode('Called '));
    var code = document.createElement('code');
    code.textContent = tool.name || 'unknown';
    title.appendChild(code);
    body.appendChild(title);

    if (tool.result_summary) {
      var summary = document.createElement('div');
      summary.className = 'aia-tool-summary';
      summary.textContent = tool.result_summary;
      body.appendChild(summary);
    }

    card.appendChild(body);
    return card;
  }

  function buildSources(sources) {
    var row = document.createElement('div');
    row.className = 'aia-sources';
    row.appendChild(document.createTextNode('Sources: '));
    sources.forEach(function (src, i) {
      if (i > 0) row.appendChild(document.createTextNode(', '));
      var url = safeUrl(src.url);
      if (url) {
        var a = document.createElement('a');
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = src.title || url;
        row.appendChild(a);
      } else {
        var span = document.createElement('span');
        span.textContent = src.title || '';
        row.appendChild(span);
      }
    });
    return row;
  }

  function renderChips(suggested) {
    var list = Array.isArray(suggested) ? suggested.filter(Boolean) : [];
    chipsEl.innerHTML = '';
    if (!list.length) {
      chipsEl.classList.add('aia-hidden');
      return;
    }
    list.slice(0, 6).forEach(function (label) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'aia-chip';
      chip.textContent = label;
      chip.addEventListener('click', function () {
        sendMessage(label);
      });
      chipsEl.appendChild(chip);
    });
    chipsEl.classList.remove('aia-hidden');
    scrollToBottom();
  }

  function showTyping(show) {
    typingEl.classList.toggle('aia-hidden', !show);
    if (show) scrollToBottom();
  }

  /* ---------------------------------------------------------------
   * 7. Open / close
   * ------------------------------------------------------------- */
  var isOpen = false;
  var greeted = false;

  function open() {
    if (isOpen) return;
    isOpen = true;
    panel.classList.remove('aia-hidden');
    // Force reflow so the enter animation plays.
    void panel.offsetWidth;
    panel.classList.remove('aia-panel-closed');
    panel.classList.add('aia-panel-open');
    bubble.setAttribute('aria-expanded', 'true');
    bubbleIconChat.classList.add('aia-hidden');
    bubbleIconClose.classList.remove('aia-hidden');
    if (!greeted && config.welcome_message) {
      greeted = true;
      addBotMessage({ reply: config.welcome_message });
    }
    window.setTimeout(function () { inputEl.focus({ preventScroll: true }); }, 220);
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    panel.classList.remove('aia-panel-open');
    panel.classList.add('aia-panel-closed');
    bubble.setAttribute('aria-expanded', 'false');
    bubbleIconChat.classList.remove('aia-hidden');
    bubbleIconClose.classList.add('aia-hidden');
    window.setTimeout(function () {
      if (!isOpen) panel.classList.add('aia-hidden');
    }, 220);
  }

  function toggle() {
    if (isOpen) close(); else open();
  }

  bubble.addEventListener('click', toggle);
  closeBtn.addEventListener('click', close);

  /* ---------------------------------------------------------------
   * 8. Chat transport (live API + demo mock)
   * ------------------------------------------------------------- */
  function chatRequest(payload) {
    // DEMO MOCK — screenshot use only, never in production.
    if (MOCK_MODE) {
      if (!window.__aiAgentMock ||
          typeof window.__aiAgentMock.chat !== 'function') {
        return Promise.reject(new Error(
          'data-mock="true" requires window.__aiAgentMock.chat()'));
      }
      return Promise.resolve().then(function () {
        return window.__aiAgentMock.chat(payload);
      });
    }
    return window.fetch(API_BASE + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      if (!res.ok) throw new Error('Chat request failed: HTTP ' + res.status);
      return res.json();
    });
  }

  var inFlight = false;

  function sendMessage(text) {
    var message = String(text == null ? '' : text).trim();
    if (!message || inFlight) return;
    inFlight = true;

    if (!isOpen) open();
    addUserMessage(message);
    inputEl.value = '';
    renderChips([]);
    showTyping(true);

    var payload = {
      tenant_id: TENANT,
      session_id: SESSION_ID,
      message: message,
      page_url: window.location.href,
      page_title: document.title
    };

    chatRequest(payload).then(function (data) {
      showTyping(false);
      inFlight = false;
      addBotMessage(data || { reply: 'Sorry, I could not process that.' });
    }).catch(function (err) {
      showTyping(false);
      inFlight = false;
      if (window.console) console.warn('[ai-agent] chat error:', err);
      addBotMessage({ reply: 'Sorry, something went wrong. Please try again.' });
    });
  }

  formEl.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage(inputEl.value);
  });

  sendBtn.disabled = false;

  /* ---------------------------------------------------------------
   * 9. Config load (live API + demo mock) and proactive trigger
   * ------------------------------------------------------------- */
  function loadConfig() {
    // DEMO MOCK — screenshot use only, never in production.
    if (MOCK_MODE) {
      if (!window.__aiAgentMock ||
          typeof window.__aiAgentMock.config !== 'function') {
        return Promise.reject(new Error(
          'data-mock="true" requires window.__aiAgentMock.config()'));
      }
      return Promise.resolve().then(function () {
        return window.__aiAgentMock.config();
      });
    }
    return window.fetch(
      API_BASE + '/api/tenants/' + encodeURIComponent(TENANT) + '/widget-config'
    ).then(function (res) {
      if (!res.ok) throw new Error('Config request failed: HTTP ' + res.status);
      return res.json();
    });
  }

  function applyConfig(cfg) {
    cfg = cfg || {};
    config.business_name = NAME_OVERRIDE ||
      cfg.business_name || config.business_name;
    config.welcome_message = cfg.welcome_message || config.welcome_message;
    if (cfg.brand_color && /^#[0-9a-fA-F]{3,8}$/.test(cfg.brand_color)) {
      root.style.setProperty('--brand', cfg.brand_color);
    }
    config.trigger = cfg.trigger || config.trigger;
    headerName.textContent = config.business_name;
    armTrigger();
  }

  function armTrigger() {
    var trig = config.trigger || {};
    if (!trig.enabled) return;
    var pages = Array.isArray(trig.pages) ? trig.pages : [];
    if (!pages.length) return;

    var path = window.location.pathname || '/';
    var matched = pages.some(function (p) {
      return p && path.indexOf(String(p)) !== -1;
    });
    if (!matched) return;

    var delayMs = Math.max(0, Number(trig.delay_sec || 0)) * 1000;
    window.setTimeout(function () {
      try {
        if (window.sessionStorage.getItem(TRIGGER_KEY)) return;
        window.sessionStorage.setItem(TRIGGER_KEY, '1');
      } catch (e) { /* sessionStorage unavailable — still trigger once */ }
      open();
      if (trig.message) addBotMessage({ reply: trig.message });
    }, delayMs);
  }

  loadConfig().then(applyConfig).catch(function (err) {
    if (window.console) console.warn('[ai-agent] config error:', err);
    // Fall back to defaults so the widget still works.
    applyConfig(null);
  });

  /* ---------------------------------------------------------------
   * 10. Public API for site triggers and demo automation
   * ------------------------------------------------------------- */
  window.__aiAgentWidget = {
    open: open,
    close: close,
    send: sendMessage
  };

  // Silence unused-helper lint warnings in strict mode.
  void esc;
})();

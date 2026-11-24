/* Left Off: the page. It shows the saved run in site/data/run.json; it decides nothing and stores nothing. */
(function () {
  "use strict";
  var D = null, current = null, listScroll = 0;
  var $ = function (id) { return document.getElementById(id); };
  var REPO = "https://github.com/Duckky153/left-off";
  var PHONE = window.matchMedia("(max-width: 760px)");

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }

  function intro() {
    var c = D.counts;
    var h = $("headline");
    h.textContent = c.shoppers + " shoppers";
    h.appendChild(document.createElement("br"));
    h.appendChild(document.createTextNode("stopped partway."));
    var sub = $("sub");
    sub.textContent = "";
    [[c.drafts, "drafts written", "draft"], [c.ready, "ready for a person to approve", "ready"], [c.person, "go to a person", "person"],
     [c.do_not_contact, "can't be contacted", "do_not_contact"]].forEach(function (x) {
      var n = el("span", "num");
      var b = el("b", "", String(x[0]));
      n.appendChild(b);
      var lab = el("span", "lab");
      if (x[2] !== "draft") lab.appendChild(el("i", "dot " + x[2]));
      lab.appendChild(document.createTextNode(x[1]));
      n.appendChild(lab);
      sub.appendChild(n);
    });
  }

  function renderList() {
    var box = $("list");
    box.textContent = "";
    var rows = el("div", "rows");
    [["ready", "Draft ready"], ["person", "Needs a person"], ["do_not_contact", "Do not contact"]].forEach(function (g) {
      var these = D.rows.filter(function (r) { return r.outcome === g[0]; });
      if (!these.length) return;
      var sec = el("div", "sec");
      var h = el("div", "group", g[1] + " ");
      h.appendChild(el("span", "count", "· " + these.length));
      sec.appendChild(h);
      rows.appendChild(sec);
      these.forEach(function (r) {
        var b = el("button", "row");
        b.type = "button";
        b.dataset.id = r.id;
        var nm = el("span", "n");
        nm.appendChild(el("i", "dot " + g[0]));
        nm.appendChild(document.createTextNode(r.name));
        b.appendChild(nm);
        b.appendChild(el("span", "a", r.outcome === "ready" ? r.ago : r.list_reason));
        b.addEventListener("click", function () { listScroll = window.scrollY; location.hash = "s-" + r.id; });
        sec.appendChild(b);
      });
    });
    box.appendChild(rows);
  }

  function journey(r) {
    var ol = el("ol", "journey");
    r.journey.steps.forEach(function (s, i) {
      ol.appendChild(el("li", i < r.journey.at ? "done" : i === r.journey.at ? "here" : "", s));
    });
    var wrap = el("div", "track");
    wrap.appendChild(ol);
    if (r.journey.date) wrap.appendChild(el("p", "when", "Stopped at " + r.journey.steps[r.journey.at].toLowerCase() + ", " + r.journey.date));
    return wrap;
  }

  function marked(text, words) {
    var frag = document.createDocumentFragment();
    if (!words || !words.length) { frag.appendChild(document.createTextNode(text)); return frag; }
    var re = new RegExp("\\b(" + words.map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("|") + ")\\b", "gi");
    var last = 0, m;
    while ((m = re.exec(text))) {
      frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      frag.appendChild(el("mark", "", m[0]));
      last = m.index + m[0].length;
    }
    frag.appendChild(document.createTextNode(text.slice(last)));
    return frag;
  }

  function renderShopper(r) {
    var box = $("shopper");
    box.textContent = "";
    var back = el("a", "back", "‹ All shoppers");
    back.href = "#shoppers";
    box.appendChild(back);
    var st = el("p", "status");
    st.appendChild(el("span", "pill " + r.outcome, r.label));
    if (r.reason && r.outcome !== "ready") st.appendChild(el("span", "why", r.reason));
    box.appendChild(st);
    box.appendChild(el("h2", "", r.name));
    box.appendChild(el("p", "facts", r.facts));
    box.appendChild(journey(r));
    var rbox = $("record");
    rbox.textContent = "";
    rbox.hidden = !(r.record && r.record.length);
    if (r.record && r.record.length) {
      var rec = el("div", "record");
      rec.appendChild(el("p", "label", "From their record"));
      var dl = el("dl");
      r.record.forEach(function (x) {
        var row = el("div", x[0] === r.used ? "used" : "");
        row.appendChild(el("dt", "", x[0]));
        var dd = el("dd", "", x[1]);
        if (x[0] === r.used) dd.appendChild(el("span", "tag", "in the draft"));
        row.appendChild(dd);
        dl.appendChild(row);
      });
      rec.appendChild(dl);
      rbox.appendChild(rec);
    }
  }

  function joined(xs) {
    return xs.length > 1 ? xs.slice(0, -1).join(", ") + " and " + xs[xs.length - 1] : xs[0];
  }

  /* why a held draft was stopped: each marked word with its reason, then the reasons with no words, then the AI check's readings */
  function stoppedLine(list) {
    var marked = list.filter(function (x) { return x.words.length; }).map(function (x) {
      return x.why.replace("{w}", x.words.map(function (w) { return "\u201C" + w + "\u201D"; }).join(", "));
    });
    var plain = list.filter(function (x) { return !x.words.length && x.by === "code"; }).map(function (x) { return x.why; });
    var read = list.filter(function (x) { return x.by === "ai"; }).map(function (x) { return x.why; });
    var out = [];
    if (marked.length) out.push("Stopped: " + marked.join("; ") + ".");
    if (plain.length) out.push((out.length ? "It also " : "Stopped: it ") + joined(plain) + ".");
    if (read.length) out.push((out.length ? "The AI check also " : "Stopped: the AI check ") + joined(read) + ".");
    if (!out.length) out.push("Stopped by a check.");
    return out.join(" ");
  }

  function incoming(r, box) {
    var c = el("div", "convo");
    c.appendChild(el("p", "when", r.question ? r.ago : r.ago + ", no question waiting"));
    if (r.question) c.appendChild(el("p", "bubble in", r.question));
    box.appendChild(c);
    return c;
  }

  /* a shopper with no message and no draft: one line in the middle of the panel */
  function emptyState(text) {
    var e = el("div", "empty");
    var ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 48 48"); svg.setAttribute("aria-hidden", "true");
    var c = document.createElementNS(ns, "circle");
    c.setAttribute("cx", "24"); c.setAttribute("cy", "24"); c.setAttribute("r", "19");
    var l = document.createElementNS(ns, "line");
    l.setAttribute("x1", "11"); l.setAttribute("y1", "37"); l.setAttribute("x2", "37"); l.setAttribute("y2", "11");
    svg.appendChild(c); svg.appendChild(l);
    e.appendChild(svg);
    e.appendChild(el("p", "", text));
    return e;
  }

  function renderPanel(r) {
    var box = $("panel");
    box.textContent = "";
    var head = el("div", "phead");
    box.appendChild(head);
    if (r.outcome === "do_not_contact") {
      if (r.question) { head.appendChild(el("h3", "", "No message")); incoming(r, box); return; }
      box.appendChild(emptyState(r.reason || r.label));
      return;
    }
    if (r.outcome === "person") {
      head.appendChild(el("h3", "", r.kind === "waiting" && r.reply_by ? "Reply due " + r.reply_by : "A person decides whether to nudge"));
      var c0 = incoming(r, box);
      if (r.held_draft) {
        var hb = el("div", "bubble out held");
        hb.appendChild(el("span", "badge", "Stopped"));
        var hp = el("p");
        hp.appendChild(marked(r.held_draft, r.caught));
        hb.appendChild(hp);
        c0.appendChild(hb);
        box.appendChild(el("p", "reason", stoppedLine(r.stopped)));
      } else if (r.strip && !r.question) {
        c0.remove();
        box.appendChild(emptyState(r.strip));
      } else if (r.strip) {
        box.appendChild(el("p", "reason", r.strip));
      }
      return;
    }
    head.appendChild(el("h3", "", r.title));
    var m = r.message, c = incoming(r, box);
    if (m.channel === "email") {
      var mail = el("div", "mail");
      mail.appendChild(el("p", "subject", m.subject));
      mail.appendChild(el("p", "", m.body));
      if (m.cta) { var cta = el("p", "cta"); cta.appendChild(el("span", "btn", m.cta)); mail.appendChild(cta); }
      mail.appendChild(el("p", "foot", "Address and unsubscribe line added when sent."));
      c.appendChild(mail);
    } else {
      c.appendChild(el("p", "bubble out", m.text));
    }
    var bar = el("p", "sendbar");
    bar.appendChild(el("span", "", (r.channel === "text" ? "Text" : "Email") + " · " + r.send_short));
    bar.appendChild(el("span", "approve", "Sends once approved"));
    box.appendChild(bar);
  }

  function select(id) {
    var r = D.rows.filter(function (x) { return x.id === id; })[0];
    if (!r) { location.replace("#shoppers"); return; }
    current = r.id;
    Array.prototype.forEach.call(document.querySelectorAll(".row"), function (b) {
      var on = b.dataset.id === r.id;
      b.setAttribute("aria-current", on ? "true" : "false");
      if (on && !PHONE.matches) b.scrollIntoView({ block: "nearest" });
    });
    renderShopper(r);
    renderPanel(r);
  }

  function renderPlan() {
    var c = D.test_plan.cautious, box = $("view-plan");
    box.textContent = "";
    var n = function (x) { return x.toLocaleString("en-US"); };
    var round = function (x) { return n(Math.round(x / 100) * 100); };
    var card = el("div", "plancard");
    box.appendChild(card);
    var big = el("div", "bignums");
    [["1 in 5", "held back at random"], ["14 days", "to take the next step"], ["about " + round(c.total), "shoppers needed"]].forEach(function (x) {
      var n = el("span", "num");
      n.appendChild(el("b", "", x[0]));
      n.appendChild(el("span", "lab", x[1]));
      big.appendChild(n);
    });
    card.appendChild(big);
    var dl = el("dl");
    [["Who gets it", "Shoppers quiet for 3 to 30 days who may be contacted and have no question waiting. Shoppers partway through a purchase still get their reminder and aren't in the test."],
     ["Held back", "1 in 5, picked at random. They get everything they get today except this nudge."],
     ["What we measure", "Per 100 shoppers, how many more take their next step within 14 days when nudged than when held back."],
     ["Also tracked", "Opt-outs, complaints, and nudges handed to a person."],
     ["Stop at once", "If any message reaches someone it shouldn't."],
     ["Decision", "Roll it out only if the nudged group is clearly ahead and opt-outs and complaints stay low."],
     ["How many", "If 8 in 100 take their next step without it (a guess), spotting a gain of 1.5 per 100 takes about " + round(c.total) +
       " shoppers (about " + round(c.held_back) + " held back, " + round(c.nudged) + " nudged)."]]
      .forEach(function (row) { dl.appendChild(el("dt", "", row[0])); dl.appendChild(el("dd", "", row[1])); });
    card.appendChild(dl);
    if (D.scores && D.scores.line) {
      var t = el("p", "tested", D.scores.line + " ");
      var a0 = el("a", "", "How it was tested");
      a0.href = REPO + "#how-it-was-tested";
      t.appendChild(a0);
      card.appendChild(t);
    }
    var more = el("p", "more");
    var a = el("a", "", "The full plan, with the math");
    a.href = REPO + "/blob/main/TEST-PLAN.md";
    more.appendChild(a);
    card.appendChild(more);
  }

  function route() {
    var h = location.hash.replace("#", "");
    var plan = h === "plan";
    $("view-plan").hidden = !plan;
    $("view-shoppers").hidden = plan;
    $("intro").hidden = plan;
    $("plan-hero").hidden = !plan;
    $("tab-plan").toggleAttribute("aria-current", plan);
    $("tab-shoppers").toggleAttribute("aria-current", !plan);
    if (plan) { $("tab-plan").setAttribute("aria-current", "page"); return; }
    $("tab-shoppers").setAttribute("aria-current", "page");
    var work = $("view-shoppers");
    var open = h.indexOf("s-") === 0;
    select(open ? h.slice(2) : (current || D.rows[0].id));
    work.classList.toggle("open", open);
    document.body.classList.toggle("open", open);
    if (PHONE.matches) window.scrollTo(0, open ? 0 : listScroll);
  }

  fetch("data/run.json").then(function (r) { return r.json(); }).then(function (data) {
    D = data;
    $("banner").hidden = !D.stand_in;
    var lab = $("sample-label");
    lab.textContent = "Sample data";
    lab.appendChild(el("span", "when", " · " + D.sample_date));
    intro();
    renderList();
    renderPlan();
    route();
    window.addEventListener("hashchange", route);
  }).catch(function () {
    $("nodata").hidden = false;
    $("view-shoppers").hidden = true;
  });
})();

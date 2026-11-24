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
    $("headline").textContent = c.shoppers + " shoppers stopped partway.";
    $("sub").textContent = "A small AI wrote " + c.drafts + " drafts; " + c.ready + " passed every check and wait for a person to approve them. " +
      c.person + " shoppers need a person and " + c.do_not_contact + " can't be contacted.";
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
        b.appendChild(el("span", "n", r.name));
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
      var li = el("li", i < r.journey.at ? "done" : i === r.journey.at ? "here" : "", s);
      if (i === r.journey.at && r.journey.date) li.appendChild(el("span", "when", "Stopped here, " + r.journey.date));
      ol.appendChild(li);
    });
    return ol;
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
    var st = el("p", "status " + r.outcome, r.label);
    if (r.reason && r.outcome === "person") { st.appendChild(document.createTextNode(" ")); st.appendChild(el("span", "why", "· " + r.reason)); }
    box.appendChild(st);
    box.appendChild(el("h2", "", r.name));
    box.appendChild(el("p", "facts", r.facts));
    box.appendChild(journey(r));
    var asked = el("div", "asked");
    asked.appendChild(el("p", "label", r.ago));
    if (r.question) asked.appendChild(el("q", "", r.question));
    box.appendChild(asked);
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

  function renderPanel(r) {
    var box = $("panel");
    box.textContent = "";
    if (r.outcome === "do_not_contact") {
      box.appendChild(el("h3", "", "No message"));
      if (r.strip) box.appendChild(el("p", "strip", r.strip));
      return;
    }
    if (r.outcome === "person") {
      box.appendChild(el("h3", "", r.kind === "waiting" && r.reply_by ? "Reply due " + r.reply_by : "A person decides whether to nudge"));
      if (r.held_draft) {
        var d = el("div", "draft");
        var p = el("p");
        p.appendChild(marked(r.held_draft, r.caught));
        d.appendChild(p);
        box.appendChild(d);
        box.appendChild(el("p", "strip", stoppedLine(r.stopped)));
      } else if (r.strip) {
        box.appendChild(el("p", "strip", r.strip));
      }
      return;
    }
    box.appendChild(el("h3", "", r.title));
    box.appendChild(el("p", "meta", (r.channel === "text" ? "Text" : "Email") + " · " + r.send_short + ", once approved"));
    var m = r.message, d2 = el("div", "draft");
    if (m.channel === "email") {
      d2.appendChild(el("p", "subject", m.subject));
      d2.appendChild(el("p", "", m.body));
      if (m.cta) { var c = el("p", "cta"); c.appendChild(el("span", "btn", m.cta)); d2.appendChild(c); }
      d2.appendChild(el("p", "foot", "Address and unsubscribe line added when sent."));
    } else {
      d2.appendChild(el("p", "", m.text));
    }
    box.appendChild(d2);
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
    box.appendChild(el("h2", "", "Does one nudge bring quiet shoppers back?"));
    box.appendChild(el("p", "", "Written before the test runs."));
    var dl = el("dl");
    var n = function (x) { return x.toLocaleString("en-US"); };
    var round = function (x) { return n(Math.round(x / 100) * 100); };
    [["Who gets it", "Shoppers quiet for 3 to 30 days who may be contacted and have no question waiting. Shoppers partway through a purchase still get their reminder and aren't in the test."],
     ["Held back", "1 in 5, picked at random. They get everything they get today except this nudge."],
     ["What we measure", "Per 100 shoppers, how many more take their next step within 14 days when nudged than when held back."],
     ["Also tracked", "Opt-outs, complaints, and nudges handed to a person."],
     ["Stop at once", "If any message reaches someone it shouldn't."],
     ["Decision", "Roll it out only if the nudged group is clearly ahead and opt-outs and complaints stay low."],
     ["How many", "If 8 in 100 take their next step without it (a guess), spotting a gain of 1.5 per 100 takes about " + round(c.total) +
       " shoppers (about " + round(c.held_back) + " held back, " + round(c.nudged) + " nudged)."]]
      .forEach(function (row) { dl.appendChild(el("dt", "", row[0])); dl.appendChild(el("dd", "", row[1])); });
    box.appendChild(dl);
    if (D.scores && D.scores.line) {
      var t = el("p", "tested", D.scores.line + " ");
      var a0 = el("a", "", "How it was tested");
      a0.href = REPO + "#how-it-was-tested";
      t.appendChild(a0);
      box.appendChild(t);
    }
    var more = el("p", "more");
    var a = el("a", "", "The full plan, with the math");
    a.href = REPO + "/blob/main/TEST-PLAN.md";
    more.appendChild(a);
    box.appendChild(more);
  }

  function route() {
    var h = location.hash.replace("#", "");
    var plan = h === "plan";
    $("view-plan").hidden = !plan;
    $("view-shoppers").hidden = plan;
    $("intro").hidden = plan;
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

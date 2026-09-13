/*
  Hostel Care — issue classifier
  Reads the complaint text and sorts it into a worker role (Plumber,
  Electrician, Carpenter, Mess) or General for anything else, plus an
  urgency level — using keyword scoring instead of a trained model.

  Also maps labels from the photo AI (MobileNet, see submit-complaint.html)
  to the same categories, so a photo can support the text-based guess.
*/
(function (global) {
  const CATEGORY_KEYWORDS = {
    Plumber: [
      "water", "tap", "taps", "faucet", "leak", "leaking", "leakage", "pipe", "pipes",
      "drain", "drainage", "clog", "clogged", "blocked", "toilet", "flush", "flushing",
      "bathroom", "washroom", "shower", "sink", "basin", "seepage", "overflow",
      "overflowing", "dripping", "drip", "geyser", "hot water", "no water",
      "water supply", "wet floor", "commode", "pipeline", "valve", "wc"
    ],
    Electrician: [
      "wire", "wires", "wiring", "switch", "switches", "socket", "sockets",
      "light", "lights", "bulb", "bulbs", "tube light", "fan", "fans", "plug",
      "electric", "electrical", "electricity", "power", "power cut", "power supply",
      "wifi", "wi-fi", "internet", "router", "network", "connection", "ac",
      "air conditioner", "cooler", "heater", "shock", "spark", "sparking",
      "short circuit", "fuse", "mcb", "current", "voltage", "charging point",
      "inverter", "tube", "flicker", "flickering"
    ],
    Carpenter: [
      "chair", "chairs", "table", "tables", "bed", "beds", "mattress", "cupboard",
      "wardrobe", "almirah", "shelf", "shelves", "desk", "lock", "locks", "door",
      "doors", "window", "windows", "wall", "walls", "ceiling", "crack", "cracks",
      "roof", "floor", "flooring", "paint", "peeling", "plaster", "hinge", "hinges",
      "handle", "curtain", "curtains", "furniture", "broken chair", "broken table",
      "study table", "loose", "termite", "woodwork"
    ],
    Mess: [
      "food", "mess", "dining", "canteen", "meal", "meals", "breakfast", "lunch",
      "dinner", "kitchen", "hygiene", "unhygienic", "cockroach", "insect", "insects",
      "fly", "flies", "spoiled", "stale", "chef", "cook", "menu", "quantity",
      "taste", "tasteless", "cold food", "raw", "undercooked", "dirty utensils",
      "plate", "plates", "canteen staff", "mess committee", "water in mess"
    ],
  };

  const HIGH_URGENCY = [
    "urgent", "emergency", "danger", "dangerous", "fire", "shock", "spark",
    "sparking", "flooding", "flood", "safety", "smoke", "broken lock", "gas",
    "food poisoning", "short circuit", "electrocut", "collapse", "unsafe",
    "intruder", "stranger", "security threat"
  ];
  const MEDIUM_URGENCY = [
    "not working", "broken", "repair", "problem", "issue", "damaged", "stuck",
    "malfunction", "leaking", "overflow", "no water", "no power", "blocked"
  ];

  const IMAGE_CATEGORY_HINTS = {
    Plumber: [
      "toilet seat", "toilet", "wash basin", "washbasin", "hand basin", "sink",
      "tub", "bathtub", "shower curtain", "shower", "faucet", "water jug",
      "water bottle", "pipe", "plunger", "drain", "soap dispenser", "bucket"
    ],
    Electrician: [
      "space heater", "table lamp", "desk lamp", "lamp", "switch", "socket",
      "plug", "power drill", "electric fan", "fan", "light bulb", "bulb",
      "television", "monitor", "desktop computer", "cellular telephone",
      "router", "modem", "extension cord", "wire", "electric", "power"
    ],
    Carpenter: [
      "four-poster", "studio couch", "rocking chair", "folding chair", "chair",
      "desk", "wardrobe", "cabinet", "china cabinet", "bookcase", "chest",
      "file", "wall clock", "window shade", "sliding door", "door", "window",
      "lock", "bed", "table"
    ],
    Mess: [
      "dining table", "plate", "tray", "food", "meal", "bowl", "cup", "spoon",
      "fork", "refrigerator", "microwave", "stove", "frying pan", "wok", "pot",
      "soup bowl", "coffee mug"
    ],
  };

  // Sort keyword/category pairs by keyword length (longest first) so a
  // specific phrase like "dining table" is checked before a generic word
  // like "table" that would otherwise shadow it and pick the wrong category.
  const SORTED_HINT_PAIRS = Object.keys(IMAGE_CATEGORY_HINTS)
    .reduce((pairs, cat) => {
      IMAGE_CATEGORY_HINTS[cat].forEach((kw) => pairs.push({ kw, cat }));
      return pairs;
    }, [])
    .sort((a, b) => b.kw.length - a.kw.length);

  function scoreCategory(text) {
    const scores = {};
    let total = 0;

    Object.keys(CATEGORY_KEYWORDS).forEach((cat) => {
      let hits = 0;
      CATEGORY_KEYWORDS[cat].forEach((kw) => {
        if (text.includes(kw)) hits += 1;
      });
      scores[cat] = hits;
      total += hits;
    });

    // Pick the best match by hit ratio relative to that category's keyword
    // list size, not raw hit count — otherwise a category with a longer
    // keyword list wins ties unfairly just because it has more entries.
    let best = "General";
    let bestRatio = 0;
    Object.keys(scores).forEach((cat) => {
      if (scores[cat] === 0) return;
      const ratio = scores[cat] / CATEGORY_KEYWORDS[cat].length;
      if (ratio > bestRatio || (ratio === bestRatio && scores[cat] > (scores[best] || 0))) {
        best = cat;
        bestRatio = ratio;
      }
    });

    const bestScore = scores[best] || 0;
    const confidence = total > 0 ? Math.min(0.6 + (bestScore / Math.max(total, 1)) * 0.35, 0.97) : 0.55;
    return { category: best, confidence };
  }

  function scorePriority(text) {
    if (HIGH_URGENCY.some((kw) => text.includes(kw))) return "high";
    if (MEDIUM_URGENCY.some((kw) => text.includes(kw))) return "medium";
    return "low";
  }

  function classify(title, description) {
    const text = ((title || "") + " " + (description || "")).toLowerCase();
    const { category, confidence } = scoreCategory(text);
    const priority = scorePriority(text);
    return {
      category,
      priority,
      confidence: Math.round(confidence * 100),
    };
  }

  // Given a raw label from the photo AI (e.g. "washbasin, handbasin"),
  // guess which of our categories it best matches. Returns null if no
  // keyword matches, rather than forcing a wrong guess.
  function hintFromImageLabel(label) {
    const lower = (label || "").toLowerCase();
    for (const pair of SORTED_HINT_PAIRS) {
      if (lower.includes(pair.kw)) return pair.cat;
    }
    return null;
  }

  // MobileNet's top guess is sometimes an unrelated ImageNet class (e.g. a
  // tap photographed at an odd angle might come back as "table"). Since the
  // model actually returns several ranked guesses, check each in order and
  // use the first one that maps to a category we recognise, rather than
  // blindly trusting rank #1.
  function hintFromLabels(labels) {
    for (let i = 0; i < labels.length; i++) {
      const hint = hintFromImageLabel(labels[i]);
      if (hint) return { hint, label: labels[i], index: i };
    }
    return { hint: null, label: labels[0] || "", index: 0 };
  }

  global.Classifier = { classify, hintFromImageLabel, hintFromLabels };
})(window);

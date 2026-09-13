/*
  Hostel Care — Gemini-based photo classifier
  Calls Google's Gemini vision model directly from the browser (no backend
  needed, since this project is a static site) to figure out what a photo
  actually shows, and sort it into one of our maintenance categories.

  IMPORTANT — API key exposure:
  Because there's no server here to hide the key, it's visible to anyone
  who views the page source. For a college project demo this is a common
  and accepted trade-off, but it is NOT safe for a real product. If you
  keep this key long-term, restrict it in Google AI Studio / Google Cloud
  Console to only work from your GitHub Pages domain (HTTP referrer
  restriction), so it can't be copied and used elsewhere.
*/
(function (global) {
  // TODO: paste your own key here (see aistudio.google.com/apikey).
  const GEMINI_API_KEY = "AIzaSyDa3BqIC7jEeZ2ZlDTaVZLBIPff45RWMC0";

  // Free-tier eligible as of 2026. If this ever stops working, check
  // https://ai.google.dev/gemini-api/docs/models for the current
  // recommended flash-tier model name.
  const GEMINI_MODEL = "gemini-2.5-flash";

  const VALID_CATEGORIES = ["Plumber", "Electrician", "Carpenter", "Mess", "General"];
  const VALID_PRIORITIES = ["low", "medium", "high"];

  function resizeImageFile(file, maxDim, quality) {
    return new Promise(function (resolve, reject) {
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = function (e) {
        const img = new Image();
        img.onerror = reject;
        img.onload = function () {
          let width = img.width;
          let height = img.height;
          if (width > height && width > maxDim) {
            height = Math.round(height * (maxDim / width));
            width = maxDim;
          } else if (height > maxDim) {
            width = Math.round(width * (maxDim / height));
            height = maxDim;
          }
          const canvas = document.createElement("canvas");
          canvas.width = width;
          canvas.height = height;
          canvas.getContext("2d").drawImage(img, 0, 0, width, height);
          resolve({ dataUrl: canvas.toDataURL("image/jpeg", quality), canvas: canvas });
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  // "data:image/jpeg;base64,/9j/4AAQ..." -> "/9j/4AAQ..."
  function stripDataUrlPrefix(dataUrl) {
    const commaIndex = dataUrl.indexOf(",");
    return commaIndex >= 0 ? dataUrl.slice(commaIndex + 1) : dataUrl;
  }

  // Sends the complaint text + photo to Gemini together, so it can use the
  // actual photo as evidence (e.g. "this is a tap", "this is a wifi
  // router") instead of being limited to a fixed list of labels.
  // Returns {category, priority, confidence} on success, or null on any
  // failure (missing key, no internet, bad response) so the caller can
  // fall back to the local text-only classifier.
  async function classify(title, description, photoBase64) {
    if (!GEMINI_API_KEY || GEMINI_API_KEY.indexOf("PASTE_YOUR") === 0) {
      console.warn("Gemini API key not set — falling back to local classifier.");
      return null;
    }
    try {
      const prompt =
        "You are sorting a hostel maintenance complaint into exactly one " +
        "of these five categories (these are worker roles/departments, " +
        "NOT descriptions of the photo's appearance):\n" +
        "- Plumber: water taps, faucets, pipes, leaks, toilets, sinks, showers, drains\n" +
        "- Electrician: wiring, switches, sockets, lights, fans, wifi/router, AC\n" +
        "- Carpenter: furniture, doors, windows, locks, beds, chairs, tables, cupboards\n" +
        "- Mess: the hostel dining hall/canteen — food quality, kitchen hygiene, " +
        "menu, canteen utensils (this is a place name, NOT a description of " +
        "clutter or untidiness — do not pick this just because the photo " +
        "looks messy or has loose wires/pipes)\n" +
        "- General: anything that doesn't clearly fit the above\n" +
        "Also pick an urgency: low, medium, or high.\n" +
        "Title: " + title + "\n" +
        "Description: " + description + "\n" +
        "Use the attached photo as the main evidence for what the object " +
        "or issue actually is, and use the text for context.\n" +
        'Reply with ONLY a JSON object, no markdown formatting, in exactly ' +
        'this shape: {"category": "...", "priority": "...", "confidence": 0-100}';

      const parts = [{ text: prompt }];
      if (photoBase64) {
        parts.push({ inline_data: { mime_type: "image/jpeg", data: photoBase64 } });
      }

      const url =
        "https://generativelanguage.googleapis.com/v1beta/models/" +
        GEMINI_MODEL + ":generateContent?key=" + GEMINI_API_KEY;

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: parts }] }),
      });

      if (!response.ok) {
        throw new Error("Gemini request failed with status " + response.status);
      }

      const data = await response.json();
      let text = (data.candidates && data.candidates[0] &&
        data.candidates[0].content && data.candidates[0].content.parts &&
        data.candidates[0].content.parts[0] &&
        data.candidates[0].content.parts[0].text) || "";
      text = text.replace(/```json/g, "").replace(/```/g, "").trim();

      const parsed = JSON.parse(text);
      if (VALID_CATEGORIES.indexOf(parsed.category) === -1) return null;

      let priority = parsed.priority;
      if (VALID_PRIORITIES.indexOf(priority) === -1) priority = "medium";

      let confidence = Number(parsed.confidence);
      if (isNaN(confidence)) confidence = 70;
      confidence = Math.max(0, Math.min(confidence, 100));

      return { category: parsed.category, priority: priority, confidence: Math.round(confidence) };
    } catch (err) {
      console.warn("Gemini classification failed, falling back to local classifier:", err);
      return null;
    }
  }

  global.GeminiVision = { classify, resizeImageFile, stripDataUrlPrefix };
})(window);

/*
 * ChillCast の一覧ページに置く計算機。依存ライブラリなしの 1 ファイル。
 *
 * NASA POWER の hourly API をブラウザから直接叩き（GET に
 * access-control-allow-origin: * が返るため preflight は起きない）、
 * 45°F Hours / Utah / Dynamic の 3 モデルを直近 10 シーズン分計算する。
 *
 * 計算式と定数は scripts/build-chillcast-pages.py および
 * Sources/ChillCast/Models/ChillModels.swift と同じものを使う。
 */
(function () {
  "use strict";

  // 取得開始は今年から数えて決める。固定日にすると年を追うごとに取得量が増え続ける。
  // 直近 10 シーズンを揃えるのに必要なのは 11 年前の 9/1 まで。
  var FETCH_START_YEARS_BACK = 11;
  var FILL_THRESHOLD = -900;
  var SEASON_COUNT = 10;
  var MIN_COVERAGE = 0.95;
  var TOP_FITS = 3;
  var STORE = "https://apps.apple.com/us/app/id6785241430";
  // 11 年分の hourly は応答が大きい。返らないまま待たせ続けないよう打ち切る。
  var FETCH_TIMEOUT_MS = 20000;
  // シーズン内でこれだけ続けて欠測していたら、そのシーズンは採用しない。
  var MAX_GAP_HOURS = 24;

  // 積算期間。北半球は UC Davis の慣行に合わせて 11/1 開始。
  var WINDOWS = {
    north: { chill: [[11, 1], [2, 28], 1], dynamic: [[9, 1], [3, 31], 1] },
    south: { chill: [[5, 1], [8, 31], 0], dynamic: [[3, 1], [9, 30], 0] }
  };
  var WINDOW_LABELS = {
    north: { chill: "1 November – 28 February", dynamic: "1 September – 31 March" },
    south: { chill: "1 May – 31 August", dynamic: "1 March – 30 September" }
  };

  function isLeap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  }

  function utahUnit(t) {
    if (t < 1.4) return 0;
    if (t < 2.4) return 0.5;
    if (t < 9.1) return 1;
    if (t < 12.4) return 0.5;
    if (t < 15.9) return 0;
    if (t < 18.0) return -0.5;
    return -1;
  }

  // Fishman & Erez (1987)
  function DynamicState() {
    this.interS = 0;
    this.portions = 0;
  }
  DynamicState.E0 = 4153.5;
  DynamicState.E1 = 12888.8;
  DynamicState.A0 = 139500.0;
  DynamicState.A1 = 2567000000000000000.0;
  DynamicState.SLOPE = 1.6;
  DynamicState.TETMLT = 277.0;
  DynamicState.AA = DynamicState.A0 / DynamicState.A1;
  DynamicState.EE = DynamicState.E1 - DynamicState.E0;
  DynamicState.prototype.step = function (celsius) {
    var tk = celsius + 273.0;
    var ftmprt = (DynamicState.SLOPE * DynamicState.TETMLT * (tk - DynamicState.TETMLT)) / tk;
    var sr = Math.exp(ftmprt);
    var xi = sr / (1.0 + sr);
    var xs = DynamicState.AA * Math.exp(DynamicState.EE / tk);
    var ak1 = DynamicState.A1 * Math.exp(-DynamicState.E1 / tk);
    var interE = xs - (xs - this.interS) * Math.exp(-ak1);
    if (interE < 1.0) {
      this.interS = interE;
    } else {
      this.portions += xi * interE;
      this.interS = interE * (1.0 - xi);
    }
  };

  function pad(value, width) {
    var text = String(value);
    while (text.length < width) text = "0" + text;
    return text;
  }

  function dayKey(year, month, day) {
    return String(year) + pad(month, 2) + pad(day, 2);
  }

  function fetchStartKey() {
    return dayKey(new Date().getUTCFullYear() - FETCH_START_YEARS_BACK, 9, 1);
  }

  function seasonBounds(hemisphere, kind, year) {
    var spec = WINDOWS[hemisphere][kind];
    var startMonth = spec[0][0], startDay = spec[0][1];
    var endMonth = spec[1][0], endDay = spec[1][1];
    var endYear = year + spec[2];
    if (endMonth === 2 && endDay === 28 && isLeap(endYear)) endDay = 29;
    return {
      start: Date.UTC(year, startMonth - 1, startDay),
      end: Date.UTC(endYear, endMonth - 1, endDay)
    };
  }

  function seasonLabel(hemisphere, year) {
    if (hemisphere === "north") return year + "–" + String(year + 1).slice(2);
    return String(year);
  }

  // 採用の条件は 2 つ。有効率が MIN_COVERAGE 以上で、MAX_GAP_HOURS 以上続く
  // 欠測が無いこと。build-chillcast-pages.py の accumulate と同じ規則。
  function accumulate(values, bounds) {
    var expected = Math.round((bounds.end - bounds.start) / 86400000) * 24 + 24;
    var fortyFive = 0, utah = 0, good = 0, gap = 0, longestGap = 0;
    var dynamic = new DynamicState();
    for (var time = bounds.start; time <= bounds.end; time += 86400000) {
      var moment = new Date(time);
      var prefix = dayKey(moment.getUTCFullYear(), moment.getUTCMonth() + 1, moment.getUTCDate());
      for (var hour = 0; hour < 24; hour++) {
        var celsius = values[prefix + pad(hour, 2)];
        if (celsius === undefined) {
          gap++;
          if (gap > longestGap) longestGap = gap;
          continue;
        }
        gap = 0;
        good++;
        if (celsius >= 0.0 && celsius <= 7.2) fortyFive += 1;
        utah += utahUnit(celsius);
        dynamic.step(celsius);
      }
    }
    if (good < expected * MIN_COVERAGE || longestGap >= MAX_GAP_HOURS) return null;
    return { fortyFive: fortyFive, utah: utah, dynamic: dynamic.portions };
  }

  function completeYears(hemisphere, dataStart, dataEnd) {
    var years = [];
    var first = new Date(dataStart).getUTCFullYear();
    var last = new Date(dataEnd).getUTCFullYear();
    for (var year = first; year <= last; year++) {
      var chill = seasonBounds(hemisphere, "chill", year);
      var dynamic = seasonBounds(hemisphere, "dynamic", year);
      if (chill.start >= dataStart && chill.end <= dataEnd &&
          dynamic.start >= dataStart && dynamic.end <= dataEnd) {
        years.push(year);
      }
    }
    return years.slice(-SEASON_COUNT);
  }

  function summarise(seasons, key) {
    var values = seasons.map(function (season) { return season[key]; });
    var total = values.reduce(function (a, b) { return a + b; }, 0);
    return {
      mean: total / values.length,
      min: Math.min.apply(null, values),
      max: Math.max.apply(null, values)
    };
  }

  function classify(requirement, meanHours) {
    if (requirement <= meanHours * 0.9) return "fits";
    if (requirement <= meanHours * 1.1) return "marginal";
    return "short";
  }

  function parseKey(key) {
    return Date.UTC(Number(key.slice(0, 4)), Number(key.slice(4, 6)) - 1, Number(key.slice(6, 8)));
  }

  // NASA POWER は不正な引数やサービス障害でも HTTP 200 のままエラー本文を返す
  // ことがある。生の TypeError を利用者に見せないよう、ここで形を確かめる。
  function analyse(payload, requestedLatitude, requestedLongitude) {
    var raw = payload && payload.properties && payload.properties.parameter
      && payload.properties.parameter.T2M;
    if (!raw || typeof raw !== "object") {
      throw new Error("NASA POWER did not return temperatures for this point.");
    }
    var values = {};
    var lastKey = null;
    for (var key in raw) {
      if (!Object.prototype.hasOwnProperty.call(raw, key)) continue;
      var value = Number(raw[key]);
      // 数値にならない値は Number() が NaN を返す。NaN は比較がすべて false に
      // なるため、しきい値だけで弾くと積算へ流れ込む。有限判定を先に置く。
      if (!(Number.isFinite(value) && value > FILL_THRESHOLD)) continue;
      values[key] = value;
      if (lastKey === null || key > lastKey) lastKey = key;
    }
    if (lastKey === null) throw new Error("NASA POWER returned no usable temperatures for this point.");

    var lastDay = parseKey(lastKey);
    // 最終日は 23 時まで揃っているときだけ「完全な日」として扱う
    var dataEnd = lastKey.slice(8) === "23" ? lastDay : lastDay - 86400000;
    var dataStart = parseKey(fetchStartKey());
    var grid = (payload.geometry && payload.geometry.coordinates) || null;
    // 半球は「要求した緯度」で決める。応答の格子座標は赤道付近で符号が
    // 変わりうるため、地点ページ（Python）と窓がずれる。
    var latitude = Number.isFinite(Number(requestedLatitude))
      ? Number(requestedLatitude)
      : (grid ? grid[1] : 0);
    var hemisphere = latitude >= 0 ? "north" : "south";

    var years = completeYears(hemisphere, dataStart, dataEnd);
    if (years.length < SEASON_COUNT) throw new Error("Not enough complete seasons at this point yet.");

    var seasons = [];
    for (var i = 0; i < years.length; i++) {
      var chill = accumulate(values, seasonBounds(hemisphere, "chill", years[i]));
      var dynamic = accumulate(values, seasonBounds(hemisphere, "dynamic", years[i]));
      if (!chill || !dynamic || !Number.isFinite(dynamic.dynamic)) {
        throw new Error("NASA POWER has gaps in the " + seasonLabel(hemisphere, years[i]) + " season here.");
      }
      seasons.push({
        label: seasonLabel(hemisphere, years[i]),
        fortyFive: chill.fortyFive,
        utah: chill.utah,
        dynamic: dynamic.dynamic
      });
    }

    return {
      hemisphere: hemisphere,
      seasons: seasons,
      stats: {
        fortyFive: summarise(seasons, "fortyFive"),
        utah: summarise(seasons, "utah"),
        dynamic: summarise(seasons, "dynamic")
      },
      version: (payload.header && payload.header.api && payload.header.api.version) || "",
      coordinates: grid || [Number(requestedLongitude) || 0, latitude]
    };
  }

  // ---- DOM ----

  var form, output, status, varieties;
  var controls = [];
  var pending = null;

  function setBusy(busy) {
    for (var i = 0; i < controls.length; i++) {
      if (controls[i]) controls[i].disabled = busy;
    }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function setStatus(message, kind) {
    status.textContent = message || "";
    status.className = "chill-status" + (kind ? " chill-status--" + kind : "");
  }

  function table(headers, rows) {
    var wrap = el("div", "chill-scroll");
    var node = el("table", "chill-table");
    var thead = el("thead");
    var headRow = el("tr");
    headers.forEach(function (header) { headRow.appendChild(el("th", null, header)); });
    thead.appendChild(headRow);
    node.appendChild(thead);
    var tbody = el("tbody");
    rows.forEach(function (row) {
      var tr = el("tr");
      row.forEach(function (cell) { tr.appendChild(el("td", null, cell)); });
      tbody.appendChild(tr);
    });
    node.appendChild(tbody);
    wrap.appendChild(node);
    return wrap;
  }

  function round(value, digits) {
    return value.toFixed(digits);
  }

  function today() {
    var now = new Date();
    return {
      key: dayKey(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate()),
      slashed: now.getUTCFullYear() + "/" + pad(now.getUTCMonth() + 1, 2) + "/" + pad(now.getUTCDate(), 2)
    };
  }

  function render(label, result) {
    output.innerHTML = "";
    var stats = result.stats;
    var coordinates = result.coordinates;
    var span = result.seasons[0].label + " to " + result.seasons[result.seasons.length - 1].label;

    output.appendChild(el("h3", null, "Chill at " + label));
    output.appendChild(el("p", "chill-note",
      "Ten seasons (" + span + ") at " + round(coordinates[1], 2) + ", " + round(coordinates[0], 2) +
      ". 45°F Hours and Utah cover " + WINDOW_LABELS[result.hemisphere].chill +
      "; Dynamic covers " + WINDOW_LABELS[result.hemisphere].dynamic + "."));

    output.appendChild(table(
      ["Model", "Average", "Lowest season", "Highest season"],
      [
        ["45°F Hours", round(stats.fortyFive.mean, 1) + " hours", round(stats.fortyFive.min, 1), round(stats.fortyFive.max, 1)],
        ["Utah", round(stats.utah.mean, 1) + " units", round(stats.utah.min, 1), round(stats.utah.max, 1)],
        ["Dynamic", round(stats.dynamic.mean, 1) + " portions", round(stats.dynamic.min, 1), round(stats.dynamic.max, 1)]
      ]
    ));

    output.appendChild(el("h4", null, "Season by season"));
    output.appendChild(table(
      ["Season", "45°F Hours", "Utah units", "Chill portions"],
      result.seasons.map(function (season) {
        return [season.label, round(season.fortyFive, 0), round(season.utah, 1), round(season.dynamic, 1)];
      })
    ));

    var meanHours = stats.fortyFive.mean;
    var fits = varieties.filter(function (variety) {
      return classify(variety.requirement, meanHours) === "fits";
    }).sort(function (a, b) { return b.requirement - a.requirement; }).slice(0, TOP_FITS);

    output.appendChild(el("h4", null, "Varieties that fit"));
    if (fits.length) {
      output.appendChild(el("p", "chill-note",
        "The " + fits.length + " most chill-demanding varieties that still fit an average of " +
        round(meanHours, 0) + " chill hours here."));
      output.appendChild(table(
        ["Variety", "Species", "Chill requirement"],
        fits.map(function (variety) {
          return [variety.name, variety.species, variety.requirement + " hours"];
        })
      ));
    } else {
      output.appendChild(el("p", "chill-note",
        "None of the bundled varieties fit an average of " + round(meanHours, 0) + " chill hours here."));
    }

    var cta = el("p");
    var link = el("a", "promo-button", "See all varieties that fit in the ChillCast app");
    link.href = STORE;
    cta.appendChild(link);
    output.appendChild(cta);
    output.appendChild(el("p", "chill-note",
      "This page shows the ten-season average only. ChillCast tracks this season's running total on your iPhone."));

    var stamp = today();
    output.appendChild(el("p", "chill-note",
      "The data was obtained from the National Aeronautics and Space Administration (NASA) Langley " +
      "Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the " +
      "NASA Earth Science Division."));
    output.appendChild(el("p", "chill-note",
      "The data was obtained from the POWER Project's Hourly " +
      String(result.version).replace(/^v/, "") + " version on " + stamp.slashed + "."));
    output.appendChild(el("p", "chill-note",
      "Values are NASA POWER regional estimates (about 0.5° grid), not orchard measurements. " +
      "Check your local extension service for station data. NASA does not endorse ChillCast."));
  }

  function calculate(latitude, longitude, label) {
    if (!isFinite(latitude) || !isFinite(longitude) ||
        latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setStatus("Enter a latitude between -90 and 90 and a longitude between -180 and 180.", "error");
      return;
    }
    output.innerHTML = "";
    setStatus("Fetching ten years of hourly temperatures from NASA POWER. This usually takes a few seconds.", "busy");

    var query = new URLSearchParams({
      parameters: "T2M",
      community: "AG",
      longitude: String(longitude),
      latitude: String(latitude),
      start: fetchStartKey(),
      end: today().key,
      format: "JSON"
    });
    var url = "https://power.larc.nasa.gov/api/temporal/hourly/point?" + query.toString();

    // 進行中の要求は打ち切り、ボタンも無効にする。連続して押したときに
    // 先の応答が後の表示を上書きするのを防ぐ。
    if (pending) pending.abort();
    var controller = new AbortController();
    pending = controller;
    setBusy(true);
    var timer = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
    // 現在の要求なら true。差し替えられた古い要求は結果を捨てる。
    var settle = function () {
      clearTimeout(timer);
      if (pending !== controller) return false;
      pending = null;
      setBusy(false);
      return true;
    };

    fetch(url, { signal: controller.signal })
      .then(function (response) {
        if (!response.ok) throw new Error("NASA POWER replied with HTTP " + response.status + ".");
        return response.json();
      })
      .then(function (payload) {
        var result = analyse(payload, latitude, longitude);
        if (!settle()) return;
        setStatus("");
        render(label, result);
        output.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (error) {
        var timedOut = error && error.name === "AbortError";
        if (!settle()) return;
        output.innerHTML = "";
        setStatus(
          timedOut
            ? "NASA POWER did not answer within " + Math.round(FETCH_TIMEOUT_MS / 1000) +
              " seconds. Try again in a minute, or open one of the location pages below."
            : "Could not calculate chill for this point. " + (error && error.message ? error.message : "") +
              " NASA POWER may be busy or offline; try again in a minute, or open one of the location pages below.",
          "error"
        );
      });
  }

  function init() {
    form = document.getElementById("chill-calculator");
    if (!form) return;
    output = document.getElementById("chill-output");
    status = document.getElementById("chill-status");

    var source = document.getElementById("chill-varieties");
    varieties = source ? JSON.parse(source.textContent) : [];

    var select = document.getElementById("chill-site");
    var latField = document.getElementById("chill-lat");
    var lonField = document.getElementById("chill-lon");
    controls = [
      select, latField, lonField,
      document.getElementById("chill-site-go"),
      document.getElementById("chill-geo-go"),
      document.getElementById("chill-manual-go")
    ];

    form.addEventListener("submit", function (event) { event.preventDefault(); });

    document.getElementById("chill-site-go").addEventListener("click", function () {
      var option = select.options[select.selectedIndex];
      if (!option || !option.value) {
        setStatus("Choose a location first.", "error");
        return;
      }
      calculate(Number(option.dataset.lat), Number(option.dataset.lon), option.text);
    });

    document.getElementById("chill-geo-go").addEventListener("click", function () {
      if (!navigator.geolocation) {
        setStatus("This browser does not offer location access. Use the list or enter coordinates.", "error");
        return;
      }
      setStatus("Asking your browser for your location…", "busy");
      navigator.geolocation.getCurrentPosition(
        function (position) {
          // 0.1° に丸めて送る。NASA POWER の格子より細かい座標は必要ない。
          var latitude = Math.round(position.coords.latitude * 10) / 10;
          var longitude = Math.round(position.coords.longitude * 10) / 10;
          calculate(latitude, longitude, "your location (" + latitude.toFixed(1) + ", " + longitude.toFixed(1) + ")");
        },
        function () {
          setStatus("Your browser did not share a location. Use the list or enter coordinates instead.", "error");
        },
        { enableHighAccuracy: false, timeout: 15000, maximumAge: 600000 }
      );
    });

    document.getElementById("chill-manual-go").addEventListener("click", function () {
      var latitude = Number(latField.value);
      var longitude = Number(lonField.value);
      if (latField.value === "" || lonField.value === "") {
        setStatus("Enter both a latitude and a longitude.", "error");
        return;
      }
      calculate(latitude, longitude, latitude.toFixed(2) + ", " + longitude.toFixed(2));
    });
  }

  // Node から Python の計算と突き合わせるための口（scripts/test_js_python_parity.py）。
  // export の有無で init() の呼び出しを止めない。ページに module を定義する別の
  // スクリプトが入っても、計算機が黙って動かなくなることはない。
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      analyse: analyse,
      utahUnit: utahUnit,
      accumulate: accumulate,
      summarise: summarise,
      seasonBounds: seasonBounds,
      completeYears: completeYears
    };
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }
})();

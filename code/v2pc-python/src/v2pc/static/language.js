(() => {
  "use strict";

  const messages = {
    "Demo didattica del protocollo Visual Two-Party Computation": "Educational demo of the Visual Two-Party Computation protocol",
    "blocco pointer 1 per 2": "1 by 2 pointer block",
    "Ingrandimento dei blocchi pointer 1 per 2": "Enlarged 1 by 2 pointer blocks",
    "Costruisci le share, segui il pointer bit e osserva la sovrapposizione trasformarsi nel risultato della funzione.": "Build the shares, follow the pointer bit and see the overlays reveal the function's result.",
    "Configurazione esperimento": "Experiment settings",
    "Funzione booleana": "Boolean function",
    "Operatori: & AND, | OR, ^ XOR, ~ NOT. Le variabili che iniziano per x sono di Alice, quelle per y di Bob.": "Operators: & AND, | OR, ^ XOR, ~ NOT. Variables starting with x belong to Alice; those starting with y belong to Bob.",
    "Valori delle variabili": "Input values",
    "Seleziona 0 oppure 1": "Select 0 or 1",
    "Scrivi una formula valida per vedere gli ingressi.": "Enter a valid formula to display its inputs.",
    "Lato immagine": "Image side length",
    "Seme (opzionale)": "Seed (optional)",
    "casuale": "random",
    "Lascia vuoto per generare una costruzione casuale": "Leave blank to generate a random construction",
    "Simula il trasferimento e ricostruisci": "Simulate transfer and reconstruct",
    "Scarica tutte le alternative": "Download all alternatives",
    "Risultato": "Result",
    "Immagine di uscita ricostruita": "Reconstructed output image",
    "Coincide con il valore booleano": "Matches the Boolean value",
    "Discordanza probabilistica": "Probabilistic mismatch",
    "Valore vero": "Boolean value",
    "Porte": "Gates",
    "Profondità": "Depth",
    "Scarica le share trasferite": "Download transferred shares",
    "Il kit contiene un’alternativa per ingresso e un PDF A4 ritagliabile.": "The kit contains one alternative per input and an A4 PDF for cutting out the shares.",
    "Separazione del protocollo": "Protocol phases",
    "Costruzione:": "Construction:",
    "Distribuzione:": "Distribution:",
    "Ricostruzione:": "Reconstruction:",
    "Le alternative scartate non entrano nella ricostruzione.": "Discarded alternatives are not used in reconstruction.",
    "il pointer recuperato seleziona la metà corretta a ogni porta.": "the recovered pointer selects the correct half at each gate.",
    "L’oblivious transfer fisico o di rete non è implementato.": "Physical or network oblivious transfer is not implemented.",
    "Circuito visuale": "Visual circuit",
    "Dalle share di ingresso, attraverso le porte, fino all’uscita.": "From input shares, through the gates, to the output.",
    "Diagramma del circuito": "Circuit diagram",
    "uscita finale": "final output",
    "Il flusso si legge dal basso verso l’alto: ogni riquadro di ingresso contiene la share e, subito al suo fianco, il pointer in chiaro e le eventuali share dei pointer associati alle porte superiori.": "Read the flow from bottom to top: each input box contains the share and, beside it, the clear pointer and any shares of pointers associated with higher gates.",
    "Scarica l’immagine del circuito": "Download circuit image",
    "Share trasferite": "Transferred shares",
    "Una sola alternativa per ogni occorrenza di input.": "One alternative per input occurrence.",
    "share con blocchi pointer 1×2 anteposti": "share with prepended 1×2 pointer blocks",
    "ingrandimento": "enlargement",
    "share dei pointer delle porte superiori": "shares of pointers for higher gates",
    "nessun pointer": "no pointer",
    "Ogni pointer è un blocco 1×2 anteposto alla parte a cui appartiene. Sul filo destro ogni pointer precede immediatamente la propria metà.": "Each pointer is a 1×2 block prepended to its corresponding part. On the right wire, each pointer immediately precedes its own half.",
    "Ricostruzione porta per porta": "Gate-by-gate reconstruction",
    "Il pointer sceglie una metà della share destra.": "The pointer selects one half of the right share.",
    "Download non riuscito.": "Download failed.",
    "Una share del circuito non è caricabile.": "A circuit share could not be loaded.",
    "Il browser non riesce a creare il file PNG.": "The browser could not create the PNG file.",
    "Preparazione del PNG…": "Preparing PNG…",
    "Il browser non rende disponibile il disegno 2D.": "The browser does not provide a 2D drawing context.",
    "Immagine scaricata.": "Image downloaded.",
    "Nella demo web il lato deve essere compreso tra 16 e 64.": "In the web demo, the image side length must be between 16 and 64.",
    "Nella demo web sono ammesse al massimo 12 porte.": "The web demo allows at most 12 gates.",
    "L'espressione deve contenere da 1 a 2000 caratteri.": "The expression must contain between 1 and 2000 characters.",
    "La costruzione supera il limite di memoria configurato; ridurre la formula o il lato delle immagini.": "The construction exceeds the configured memory limit; use a smaller formula or image side length.",
    "Espressione non valida: usare nomi di variabile, parentesi e gli operatori & (AND), | (OR), ^ (XOR), ~ (NOT).": "Invalid expression: use variable names, parentheses and the operators & (AND), | (OR), ^ (XOR), ~ (NOT).",
  };

  const patterns = [
    [/^Share selezionata di (.+) con blocchi pointer$/, (_, name) => `Selected share for ${name} with pointer blocks`],
    [/^Share immagine di (.+) con blocchi pointer$/, (_, name) => `Share image for ${name} with pointer blocks`],
    [/^Porta (.+)$/, (_, gate) => `${gate} gate`],
    [/^Share in uscita dalla porta (.+)$/, (_, gate) => `Output share of the ${gate} gate`],
    [/^Uscita della porta (.+)$/, (_, gate) => `Output of the ${gate} gate`],
    [/^uscita ([01])$/, (_, bit) => `output ${bit}`],
    [/^letto ([01])$/, (_, bit) => `read ${bit}`],
    [/^pointer in chiaro = (.+)$/, (_, bit) => `clear pointer = ${bit}`],
    [/^pointer ([01]) · metà (sinistra|destra)$/, (_, bit, half) => `pointer ${bit} · ${half === "sinistra" ? "left" : "right"} half`],
    [/^(\d+) alternative generate senza usare gli input\.$/, (_, count) => `${count} alternatives generated without using input values.`],
    [/^(\d+) share di Alice consegnate direttamente; (\d+) share di Bob scelte mediante OT simulato\.$/, (_, alice, bob) => `${alice} Alice shares delivered directly; ${bob} Bob shares selected through simulated OT.`],
    [/^(\d+) share con parte non assegnata sono scelte localmente\.$/, (_, count) => `${count} shares with no assigned party are selected locally.`],
    [/^(filo sinistro|filo destro|filo di uscita) · (Alice|Bob|parte non assegnata) · (consegna diretta|OT simulato|selezione locale)$/, (_, role, party, delivery) => `${{"filo sinistro": "left wire", "filo destro": "right wire", "filo di uscita": "output wire"}[role]} · ${party === "parte non assegnata" ? "unassigned party" : party} · ${{"consegna diretta": "direct delivery", "OT simulato": "simulated OT", "selezione locale": "local selection"}[delivery]}`],
    [/^Espressione non valida: (.+)$/, (_, detail) => `Invalid expression: ${detail}`],
    [/^Assegnamento non valido: (.+)$/, (_, detail) => `Invalid assignment: ${detail}`],
    [/^Variabile ripetuta: (.+)$/, (_, detail) => `Duplicate variable: ${detail}`],
    [/^Valori mancanti: (.+)$/, (_, detail) => `Missing values: ${detail}`],
    [/^Variabili non presenti nella funzione: (.+)$/, (_, detail) => `Variables not present in the function: ${detail}`],
    [/^Valori diversi da 0 e 1: (.+)$/, (_, detail) => `Values other than 0 and 1: ${detail}`],
    [/^Manca il valore di (.+)\.$/, (_, name) => `Missing value for ${name}.`],
    [/^(.+) deve valere 0 oppure 1\.$/, (_, name) => `${name} must be 0 or 1.`],
  ];

  let language = "it";
  try {
    if (localStorage.getItem("v2pc-language") === "en") language = "en";
  } catch (_) { /* Storage can be disabled; the switch still works. */ }

  function translate(text, target = language) {
    if (target !== "en") return text;
    const key = text.replace(/\s+/g, " ").trim();
    let translated = messages[key];
    if (!translated) {
      for (const [pattern, replacement] of patterns) {
        if (pattern.test(key)) {
          translated = key.replace(pattern, replacement);
          break;
        }
      }
    }
    for (const [prefix, english] of [
      ["Impossibile creare il kit di stampa: ", "Could not create the print kit: "],
      ["Impossibile creare tutte le share: ", "Could not create all shares: "],
    ]) {
      if (key.startsWith(prefix)) translated = english + translate(key.slice(prefix.length), target);
    }
    if (!translated) return text;
    return (text.match(/^\s*/)?.[0] ?? "") + translated + (text.match(/\s*$/)?.[0] ?? "");
  }

  const texts = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.parentElement.closest("script, style, option, legend, .share-title, .circuit-input-heading, [data-no-translate]") && node.textContent.trim()) {
      texts.push([node, node.textContent]);
    }
  }
  const attributes = [];
  document.querySelectorAll("[alt], [title], [placeholder], [aria-label], meta[name=description]").forEach((node) => {
    for (const name of ["alt", "title", "placeholder", "aria-label", "content"]) {
      if (node.hasAttribute(name)) attributes.push([node, name, node.getAttribute(name)]);
    }
  });

  function setLanguage(value) {
    language = value === "en" ? "en" : "it";
    document.documentElement.lang = language;
    for (const [node, original] of texts) node.textContent = translate(original);
    for (const [node, name, original] of attributes) node.setAttribute(name, translate(original));
    const selector = document.querySelector("#language");
    if (selector) selector.value = language;
    try { localStorage.setItem("v2pc-language", language); } catch (_) { /* Optional persistence. */ }
    document.dispatchEvent(new Event("v2pc:languagechange"));
  }

  window.v2pcI18n = { translate, get language() { return language; } };
  document.querySelector("#language")?.addEventListener("change", (event) => setLanguage(event.target.value));
  setLanguage(language);
})();

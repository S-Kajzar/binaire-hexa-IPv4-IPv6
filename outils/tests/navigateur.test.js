// Tests navigateur (Playwright) : node outils/tests/navigateur.test.js [dossier-captures]
"use strict";
const path = require("path");
const { chromium } = require("playwright");

const URL = "file://" + path.join(__dirname, "..", "..", "index.html");
const SHOTS = process.argv[2];
const JUSTE = {
  q1_1: "8 bits", q1_2: "11000000.10101000.00000001.00000010", q1_3: "256", q1_4: "16 bits", q1_5: "65 536",
  q1_6: "32 bits", q1_7: "4 294 967 296", q2_1: "14", q2_2: "1110", q2_3: "4 bits", q2_4: "60447",
  q2_5: "1110 1100 0001 1111", q2_6: "16 bits", q2_7: "128 bits", q2_8: "3,4 × 10^38",
  q3_1: "-15,625", q3_2: "728,25", q3_3: "-35,5",
};
let fail = 0;
function check(cond, msg) { if (!cond) { fail++; console.error("ÉCHEC :", msg); } else console.log("ok :", msg); }

async function page(browser, w) {
  const p = await browser.newPage({ viewport: { width: w || 1280, height: 900 } });
  p.errors = [];
  p.on("pageerror", (e) => p.errors.push(e.message));
  p.on("console", (m) => { if (m.type() === "error") p.errors.push(m.text()); });
  await p.goto(URL);
  return p;
}

(async () => {
  const browser = await chromium.launch();

  // ---------- Accueil ----------
  let p = await page(browser);
  check(await p.isVisible("#home"), "accueil visible");
  check(!(await p.isVisible("main.page")), "sujet masqué avant le choix du mode");
  if (SHOTS) await p.screenshot({ path: path.join(SHOTS, "accueil.png"), fullPage: true });

  // ---------- Entraînement : tout juste = 20/20 ----------
  await p.click("[data-mode=training]");
  check(await p.isVisible("main.page"), "sujet visible en entraînement");
  for (const [id, v] of Object.entries(JUSTE)) {
    await p.fill(`#in-${id}`, v);
    await p.click(`#${id} .btn-validate`);
  }
  const score = await p.textContent("#score-val");
  check(score.startsWith("20,0"), "bandeau 20/20 après un sujet parfait (" + score + ")");
  check((await p.textContent("tfoot .final-note")).startsWith("20,0"), "récapitulatif 20/20");
  check(await p.isDisabled("#in-q1_1"), "réponse verrouillée après validation");
  check(await p.isVisible("#q1_1 .q-expl"), "démarche affichée après validation");
  check((await p.locator(".btn-print").count()) === 1, "un seul bouton « Imprimer ma copie »");
  await p.click(".tab[data-doc=DT2]");
  check(await p.isVisible("#doc-DT2"), "document DT2 ouvert depuis le rail");
  await p.click(".tab[data-doc=DT1]");
  await p.click("#partie-1 .doc-chip[data-doc=DP1]");
  check(await p.isVisible("#doc-DP1"), "document DP1 ouvert depuis un en-tête de question");
  if (SHOTS) await p.screenshot({ path: path.join(SHOTS, "entrainement-docs.png") });
  await p.keyboard.press("Escape");
  check(!(await p.isVisible("#doc-DP1")), "panneau refermé avec Échap");
  if (SHOTS) {
    await p.locator("#partie-1").screenshot({ path: path.join(SHOTS, "partie1.png") });
    await p.emulateMedia({ media: "print" });
    await p.pdf({ path: path.join(SHOTS, "copie-entrainement.pdf"), format: "A4" });
    await p.emulateMedia({ media: "screen" });
  }
  check(p.errors.length === 0, "aucune erreur JavaScript en entraînement " + p.errors.join(" | "));

  // ---------- Entraînement : demi-point d'unité ----------
  p = await page(browser);
  await p.click("[data-mode=training]");
  await p.fill("#in-q1_1", "8");
  await p.click("#q1_1 .btn-validate");
  check(await p.locator("#q1_1.is-half").count() === 1, "valeur sans unité → demi-point (orange)");
  check((await p.textContent("#q1_1 .q-unit-msg")).includes("Unité manquante"), "message « Unité manquante »");
  check((await p.textContent("#score-val")).startsWith("10,0"), "note provisoire 10/20 après un demi-point");

  // ---------- Examen ----------
  p = await page(browser, 420);
  await p.click("[data-mode=exam]");
  check(!(await p.isVisible("#q1_1 .btn-validate")), "pas de bouton Valider en examen");
  check((await p.textContent(".exam-state")) === "Note masquée", "note masquée en examen");
  await p.fill("#in-q1_1", "8 bits");
  await p.fill("#in-q2_4", "60447");
  await p.fill("#in-q3_1", "15,625");
  await p.emulateMedia({ media: "print" });
  check(!(await p.isVisible("#q1_1 .q-expl")), "impression avant remise : aucun corrigé");
  check(await p.isVisible(".print-nograde"), "impression avant remise : « Copie non corrigée »");
  await p.emulateMedia({ media: "screen" });
  if (SHOTS) await p.screenshot({ path: path.join(SHOTS, "examen-mobile.png") });
  await p.click("#exam-submit");
  check((await p.textContent("#exam-warn")).includes("15 réponse(s) encore vide(s)"), "confirmation annonce les réponses vides");
  await p.click("#exam-submit");
  check(await p.isDisabled("#in-q1_1"), "tout est verrouillé après la remise");
  check(await p.isVisible("#q1_1 .q-expl"), "corrections dévoilées après la remise");
  check(await p.locator("#q3_1.is-ko").count() === 1, "réponse fausse marquée en rouge");
  const fin = await p.textContent("tfoot .final-note");
  // P1 : 1/8 → 2,5 ; P2 : 2/10 → 4 ; P3 : 0 ; pondéré : 2,5×0,25 + 4×(1/3) = 1,96 → 2,0
  check(fin.startsWith("2,0"), "note pondérée après remise (" + fin + ")");
  const t1 = await p.textContent("#timer-val");
  await p.waitForTimeout(1200);
  check(t1 === (await p.textContent("#timer-val")), "chronomètre arrêté après la remise");
  check(p.errors.length === 0, "aucune erreur JavaScript en examen " + p.errors.join(" | "));

  await browser.close();
  console.log(fail ? fail + " échec(s)" : "Tous les tests navigateur passent");
  process.exit(fail ? 1 : 0);
})();

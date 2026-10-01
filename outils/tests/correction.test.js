// Tests du moteur de correction sur les réponses du sujet : node outils/tests/correction.test.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const html = fs.readFileSync(path.join(__dirname, "..", "..", "index.html"), "utf8");
const grading = html.match(/\/\*GRADING-START\*\/([\s\S]*?)\/\*GRADING-END\*\//)[1];
const cfg = html.match(/window\.__QCFG__ = (\{[\s\S]*?\});\n/)[1];
const ctx = { module: { exports: {} } };
vm.createContext(ctx);
vm.runInContext(grading, ctx);
const G = ctx.module.exports;
const QCFG = JSON.parse(cfg);

// [réponse saisie, score attendu]
const CASES = {
  q1_1: [["8 bits", 1], ["8bits", 1], ["8 bit", 1], ["1 octet", 1], ["8", 0.5], ["8 octets", 0.5], ["1", 0], ["7 bits", 0], ["256", 0]],
  q1_2: [["11000000.10101000.00000001.00000010", 1], ["11000000 10101000 00000001 00000010", 1],
         ["11000000101010000000000100000010", 1], ["11000000.10101000.1.10", 0], ["192.168.1.2", 0]],
  q1_3: [["256", 1], ["254", 1], ["2^8 = 256", 1], ["255", 0], ["8", 0]],
  q1_4: [["16 bits", 1], ["2 octets", 1], ["16", 0.5], ["2", 0]],
  q1_5: [["65536", 1], ["65 536", 1], ["65534", 1], ["65 535", 0]],
  q1_6: [["32 bits", 1], ["4 octets", 1], ["32", 0.5], ["32 Bits", 1]],
  q1_7: [["4294967296", 1], ["4 294 967 296", 1], ["2^32 = 4 294 967 296", 1], ["4294967295", 0], ["4,3 milliards", 0]],
  q2_1: [["14", 1], ["E = 14", 1], ["15", 0]],
  q2_2: [["1110", 1], ["0000 1110", 1], ["1111", 0], ["0111", 0]],
  q2_3: [["4 bits", 1], ["4", 0.5], ["8 bits", 0]],
  q2_4: [["60447", 1], ["60 447", 1], ["60 446", 0], ["ec1f", 0]],
  q2_5: [["1110 1100 0001 1111", 1], ["1110110000011111", 1], ["1110 1100 1 1111", 0]],
  q2_6: [["16 bits", 1], ["2 octets", 1], ["16", 0.5]],
  q2_7: [["128 bits", 1], ["16 octets", 1], ["128", 0.5], ["128 octets", 0.5], ["64 bits", 0]],
  q2_8: [["3,4 × 10^38", 1], ["3.4e38", 1], ["3,4x10^38", 1], ["3,40 * 10^38", 1],
         ["340282366920938463463374607431768211456", 1], ["2^128 = 3,4e38", 1],
         ["3,3e38", 0], ["4,3e9", 0], ["3,4e37", 0]],
  q3_1: [["-15,625", 1], ["−15.625", 1], ["- 15,625", 1], ["15,625", 0], ["-15,6", 0]],
  q3_2: [["728,25", 1], ["728.25", 1], ["+728,25", 1], ["-728,25", 0], ["728", 0]],
  q3_3: [["-35,5", 1], ["-35.50", 1], ["35,5", 0], ["-35", 0]],
};

let fail = 0, n = 0;
for (const id of Object.keys(QCFG)) {
  if (!CASES[id]) { console.error("Aucun test pour", id); fail++; continue; }
}
for (const [id, cases] of Object.entries(CASES)) {
  for (const [ans, want] of cases) {
    n++;
    const r = G.grade(ans, QCFG[id].grader);
    const got = r.invalid ? 0 : r.score;
    if (got !== want) { fail++; console.error(`ÉCHEC ${id} « ${ans} » : attendu ${want}, obtenu ${got}`, r); }
  }
}
console.log(`${n - fail} / ${n} cas réussis`);
process.exit(fail ? 1 : 0);

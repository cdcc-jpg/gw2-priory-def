const fs = require('fs');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');
const reasoner = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/reasoner/dist/index.js');

const inputPath = process.argv[2];
const content = fs.readFileSync(inputPath, 'utf-8');

const ontology = catalog.parseTurtle(content, "http://www.w3.org/2002/07/owl#");

const r = new reasoner.Reasoner(ontology);
const report = r.runAll();

console.log("Consistent:", report.isConsistent);
console.log("Unsatisfiable classes:", report.unsatisfiableClasses);
console.log("Duration:", report.durationMs, "ms");
console.log("Inferred subsumptions count:", report.inferredSubsumptions.length);

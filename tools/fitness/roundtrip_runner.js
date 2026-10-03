const fs = require('fs');
const path = require('path');
const core = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/core/dist/index.js');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

const content = fs.readFileSync(inputPath, 'utf-8');

try {
  const ontology = catalog.parseTurtle(content, "http://www.w3.org/2002/07/owl#");
  const serialized = catalog.serializeTurtle(ontology);
  fs.writeFileSync(outputPath, serialized);
  console.log("Success");
} catch (e) {
  console.error("Error:", e);
}

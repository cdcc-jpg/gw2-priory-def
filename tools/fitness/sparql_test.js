const fs = require('fs');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');
const sparql = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/sparql/dist/index.js');

const inputPath = process.argv[2];
const content = fs.readFileSync(inputPath, 'utf-8');

const ontology = catalog.parseTurtle(content, "http://www.w3.org/2002/07/owl#");

const engine = new sparql.SparqlEngine(ontology);

const query = `
SELECT ?subject ?predicate ?object
WHERE {
  ?subject ?predicate ?object .
} LIMIT 5
`;

try {
  const result = engine.query(query);
  console.log("SPARQL Success. Results:", result.length);
} catch (e) {
  console.log("SPARQL Error:", e.message);
}

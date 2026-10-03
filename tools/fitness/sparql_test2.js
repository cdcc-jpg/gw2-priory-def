const fs = require('fs');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');
const sparql = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/sparql/dist/index.js');

const inputPath = process.argv[2];
const content = fs.readFileSync(inputPath, 'utf-8');
const ontology = catalog.parseTurtle(content, "http://www.w3.org/2002/07/owl#");
const engine = new sparql.SparqlEngine(ontology);

const queries = [
  "SELECT * WHERE { ?s ?p ?o } LIMIT 5",
  "SELECT * WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?o } LIMIT 5",
  "SELECT * WHERE { ?s ?p ?o UNION { ?s ?p ?x } } LIMIT 1",
  "SELECT * WHERE { OPTIONAL { ?s ?p ?o } } LIMIT 1"
];

for (let q of queries) {
  try {
    const r = engine.query(q);
    console.log("Query:", q);
    console.log("Result:", r.bindings ? r.bindings.length : r);
  } catch (e) {
    console.log("Query failed:", q);
    console.log("Error:", e.message);
  }
}

const fs = require('fs');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');
const sparql = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/sparql/dist/index.js');
const ontology = catalog.parseTurtle(fs.readFileSync(process.argv[2], 'utf-8'), "http://www.w3.org/2002/07/owl#");
const engine = new sparql.SparqlEngine(ontology);
try {
  engine.query("SELECT * WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#subClassOf>* ?o } LIMIT 1");
  console.log("Property paths supported");
} catch (e) {
  console.log("Property paths not supported:", e.message);
}

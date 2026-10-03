const fs = require('fs');
const catalog = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/catalog/dist/index.js');
const reasoner = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/reasoner/dist/index.js');
const sparql = require('/Users/clementd/Documents/GitHub/leurn-app-ontology-tool/packages/sparql/dist/index.js');

let start = performance.now();
const content = fs.readFileSync('/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/priory_core.ttl', 'utf-8');
const ontology = catalog.parseTurtle(content, "http://www.w3.org/2002/07/owl#");
console.log("Load time:", performance.now() - start, "ms");

start = performance.now();
const r = new reasoner.Reasoner(ontology);
r.classify();
console.log("Classification time:", performance.now() - start, "ms");

start = performance.now();
const engine = new sparql.SparqlEngine(ontology);
engine.query("SELECT * WHERE { ?s ?p ?o }");
console.log("SPARQL time (all triples):", performance.now() - start, "ms");

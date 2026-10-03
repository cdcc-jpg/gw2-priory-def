import sys
import rdflib
from rdflib.compare import isomorphic, graph_diff

def main():
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    g1 = rdflib.Graph()
    g1.parse(file1, format="turtle")
    
    g2 = rdflib.Graph()
    g2.parse(file2, format="turtle")
    
    print(f"Original triples: {len(g1)}")
    print(f"Serialized triples: {len(g2)}")
    
    iso = isomorphic(g1, g2)
    print(f"Isomorphic: {iso}")
    
    if not iso:
        in_both, in_first, in_second = graph_diff(g1, g2)
        print(f"In original but not serialized (lost): {len(list(in_first))}")
        print(f"In serialized but not original (added): {len(list(in_second))}")
        for t in list(in_first)[:10]:
            print(" LOST:", t)

if __name__ == "__main__":
    main()

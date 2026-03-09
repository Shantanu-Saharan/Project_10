import json
import networkx as nx
import matplotlib.pyplot as plt
import os
import sys

# 1. Ensure the script can see the 'src' folder
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

def generate_knowledge_graph():
    # 2. Path to your extracted data
    data_path = os.path.join(script_dir, "data", "extracted_memories.json")
    
    if not os.path.exists(data_path):
        print(f"❌ Error: Could not find {data_path}. Did you run the extraction yet?")
        return

    # 3. Load the data
    with open(data_path, "r") as f:
        data = json.load(f)

    # 4. Build the Graph
    G = nx.Graph()
    for email in data:
        for rel in email.get('relationships', []):
            G.add_edge(rel['source_entity'], 
                    rel['target_entity'], 
                    relation=rel['relation_type'])

    # 5. Filter: Remove "lonely" nodes (keep only those with > 1 connection)
    nodes_to_keep = [node for node, degree in dict(G.degree()).items() if degree > 1]
    subgraph = G.subgraph(nodes_to_keep)

    # 6. Visualization Settings
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(subgraph, k=0.6, iterations=50)
    
    # Draw nodes and labels
    nx.draw_networkx_nodes(subgraph, pos, node_size=2500, node_color='lightgreen', alpha=0.9)
    nx.draw_networkx_labels(subgraph, pos, font_size=9, font_weight='bold')
    
    # Draw edges
    nx.draw_networkx_edges(subgraph, pos, width=1.0, edge_color='gray', alpha=0.4)

    plt.title("Layer10 Internship: Enron Entity Knowledge Graph", fontsize=16)
    plt.axis('off')
    
    # 7. SAVE the result as an image
    output_image = "enron_knowledge_graph.png"
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"✅ Success! Knowledge Graph saved as: {output_image}")
    
    # Optional: Show it on screen
    plt.show()

if __name__ == "__main__":
    generate_knowledge_graph()
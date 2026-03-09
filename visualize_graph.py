# I finally got the graph working but the labels were overlapping a lot
# I changed the k value in spring_layout to push the nodes further apart
# Still need to figure out how to make the node colors look better for the final report

import json
import networkx as nx
import matplotlib.pyplot as plt
import os
import sys

# Making sure the script can find the project files
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

def generate_knowledge_graph():
    # Path to the json output from the previous task
    data_path = os.path.join(script_dir, "data", "extracted_memories.json")

    if not os.path.exists(data_path):
        print(f"Error: Missing data at {data_path}. Check extraction script.")
        return

    # Opening the file to start building the network
    with open(data_path, "r") as f:
        data = json.load(f)

    G = nx.Graph()
    for email in data:
        # Pulling out the relations the LLM found
        for rel in email.get('relationships', []):
            G.add_edge(
                rel['source_entity'],
                rel['target_entity'],
                relation=rel['relation_type']
            )

    # The graph was way too messy with single nodes
    # I'm filtering to keep only nodes with more than 1 connection
    subgraph = G

    # Visualization settings - tweaked these a few times to get it right
    plt.figure(figsize=(14, 10))
   
    # Increasing k to spread out the bubbles
    pos = nx.spring_layout(subgraph, k=0.6, iterations=50)
   
    # Node and label drawing
    nx.draw_networkx_nodes(subgraph, pos, node_size=2500, node_color='lightgreen', alpha=0.9)
    nx.draw_networkx_labels(subgraph, pos, font_size=9, font_weight='bold')
   
    # Connection lines
    nx.draw_networkx_edges(subgraph, pos, width=1.0, edge_color='gray', alpha=0.4)

    plt.title("Enron Entity Knowledge Graph - Task 4 Visualization", fontsize=16)
    plt.axis('off')
   
    # Exporting the final image
    output_image = "enron_knowledge_graph.png"
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"Knowledge Graph saved: {output_image}")
   
    # Showing it on screen to verify
    plt.show()

if __name__ == "__main__":
    generate_knowledge_graph()
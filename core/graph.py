import geopandas as gpd
import networkx as nx
from libpysal.weights import Rook
import warnings
warnings.filterwarnings('ignore')

SHAPEFILE_PATH = 'data/GA-shapefiles/GA_precincts16.shp'

NODE_ATTRS = ['TOTPOP', 'VAP', 'BVAP', 'WVAP', 'CD', 'PRES16D', 'PRES16R']


def build_graph(shapefile_path=SHAPEFILE_PATH):
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(epsg=26917)
    w = Rook.from_dataframe(gdf, silence_warnings=True)
    G = w.to_networkx()
    for col in [c for c in NODE_ATTRS if c in gdf.columns]:
        nx.set_node_attributes(G, dict(enumerate(gdf[col])), name=col)
    assert nx.is_connected(G), "Graph is disconnected"
    return G, gdf


if __name__ == '__main__':
    G, gdf = build_graph()
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Connected: {nx.is_connected(G)}")

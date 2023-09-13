import logging
from model_extraction import read_vfg, extract_model, config_logger

logger = logging.getLogger(__name__)
config_logger(logger)

if __name__ == '__main__':
    vfg = read_vfg('examples/tf2/vfg.dot')
    logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    # starting_nodes = [1482, 77486, 77491, 1546, 1551, 77533, 77528]
    # starting_nodes = [1482, 1546, 1551]
    starting_nodes = [1479, 1543]
    logger.info("Starting nodes: %s", starting_nodes)
    model = extract_model(vfg, starting_nodes)
    model.write("examples/tf2/model.dot", 'Model')

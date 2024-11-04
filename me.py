import logging
from model_extraction import read_vfg, extract_model, config_logger

logger = logging.getLogger(__name__)
config_logger(logger)

if __name__ == '__main__':
    vfg = read_vfg('examples/tf2/vfg.dot')
    logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    starting_nodes = [1479, 1543]
    logger.info("Starting nodes: %s", starting_nodes)
    model = extract_model(vfg, starting_nodes)
    model.write("examples/tf2/model.dot", 'tf2')

    # vfg = read_vfg('examples/scale_publisher/vfg.dot')
    # logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    # # starting_nodes = [795]
    # starting_nodes = [41733, 41727]
    # # starting_nodes = [1180]
    # # starting_nodes = [25185, 25174, 18543]
    # logger.info("Starting nodes: %s", starting_nodes)
    # model = extract_model(vfg, starting_nodes)
    # model.write("examples/scale_publisher/model.dot", 'scale_publisher')

    # vfg = read_vfg('examples/turtle/vfg.dot')
    # logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    # starting_nodes = [180231]
    # logger.info("Starting nodes: %s", starting_nodes)
    # model = extract_model(vfg, starting_nodes)
    # model.write("examples/turtle/model.dot", 'turtle')

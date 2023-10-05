from model_builder import get_logger, Graph, VFG, Model

logger = get_logger(__name__)


def scale_publisher():
    # vfg = VFG.from_file('examples/scale_publisher/full_svfg.dot')
    vfg = VFG.from_file('examples/scale_publisher/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    starting_node_ids = {664, 668, 41733, 41727}
    logger.info("Starting nodes: %s", starting_node_ids)
    model = Model(vfg, starting_node_ids)
    model.write('examples/scale_publisher/model.dot', 'scale_publisher model', 'scale_publisher model')


def tf2():
    starting_node_ids = {1473, 1537}
    # starting_node_ids = {1473}
    # starting_node_ids = {1537}
    logger.info("Starting nodes: %s", starting_node_ids)

    vfg = VFG.from_file('examples/tf2/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    logger.info("Building model from VFG...")
    vfg_model = Model(vfg, starting_node_ids)
    vfg_model.write('examples/tf2/vfg_model.dot', 'tf2 model', 'tf2 model')

    # svfg = VFG.from_file('examples/tf2/full_svfg.dot')
    # logger.info("SVFG scale: %s", svfg.size)
    # logger.info("Building model from SVFG...")
    # svfg_model = Model.build_model(svfg, starting_node_ids)
    # svfg_model.write('examples/tf2/svfg_model.dot', 'tf2 model', 'tf2 model')


def turtle():
    starting_node_ids = {180231}
    logger.info("Starting nodes: %s", starting_node_ids)

    vfg = VFG.from_file('examples/turtle/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    model = Model(vfg, starting_node_ids)
    model.write('examples/turtle/model.dot', 'turtle model', 'turtle model')


if __name__ == '__main__':
    # scale_publisher()
    tf2()
    # turtle()

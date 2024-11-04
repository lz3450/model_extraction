from model_builder import get_logger, VFG, Model

logger = get_logger(__name__)


def scale_publisher():
    starting_node_ids = {1158, 709, 658, 662, 18249, 39268, 41755}
    logger.info("Starting nodes: %s", starting_node_ids)

    vfg = VFG.from_file('examples/scale_publisher/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    logger.info("Building model from VFG...")

    vfg_model = Model(vfg, starting_node_ids)
    vfg_model.write('examples/scale_publisher/vfg_model.dot', 'scale_publisher model', 'scale_publisher model')


def tf2():
    starting_node_ids = {1473, 1537}
    # starting_node_ids = {1473}
    # starting_node_ids = {1537}
    logger.info("Starting nodes: %s", starting_node_ids)

    vfg = VFG.from_file('examples/tf2/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    logger.info("Building model from VFG...")

    original_model = Model(vfg, starting_node_ids, False)
    original_model.write('examples/tf2/model_original.dot', 'tf2 model', 'tf2 model')

    vfg_model = Model(vfg, starting_node_ids, True)
    vfg_model.write('examples/tf2/model_vfg.dot', 'tf2 model', 'tf2 model')

    # svfg = VFG.from_file('examples/tf2/full_svfg.dot')
    # logger.info("SVFG scale: %s", svfg.size)
    # logger.info("Building model from SVFG...")
    # svfg_model = Model.build_model(svfg, starting_node_ids)
    # svfg_model.write('examples/tf2/svfg_model.dot', 'tf2 model', 'tf2 model')


def turtle():
    starting_node_ids = {45757, 45758, 45759}
    logger.info("Starting nodes: %s", starting_node_ids)

    vfg = VFG.from_file('examples/turtle/vfg.dot')
    logger.info("VFG scale: %s", vfg.size)
    logger.info("Building model from VFG...")

    original_model = Model(vfg, starting_node_ids, False)
    original_model.write('examples/turtle/model_original.dot', 'turtle model', 'turtle model')

    vfg_model = Model(vfg, starting_node_ids)
    vfg_model.write('examples/turtle/vfg_model.dot', 'turtle model', 'turtle model')


if __name__ == '__main__':
    # scale_publisher()
    # tf2()
    turtle()

from model_builder import get_logger, Graph, VFG, Model

logger = get_logger(__name__)


def test0():
    graph = Graph.from_file('examples/tf2/vfg.dot')
    print(graph)
    graph.write('test0.dot')
    graph = Graph.from_file('test0.dot')
    print(graph)


def test1():
    vfg = VFG.from_file("examples/tf2/vfg.dot")
    print(vfg)
    vfg.write('test1.dot', 'test 1', 'Test 1')


def test2():
    vfg = VFG.from_file('examples/tf2/vfg.dot')
    logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    starting_node_ids = {1479, 1543}
    logger.info("Starting nodes: %s", starting_node_ids)
    model = Model.build_model(vfg, starting_node_ids)
    model.write('model.dot', 'tf2', 'tf2')


if __name__ == '__main__':
    # test0()
    # test1()
    test2()

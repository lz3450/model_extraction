from graphviz import Digraph

def create_dot_file_ddfg():
    dot = Digraph("Listener Dataflow", format="dot")
    dot.attr(rankdir="LR")

    for node in ["/scale", "/turtle2/cmd_vel"]:
        dot.node(node, node, shape="rectangle")

    for node in ["scale_rotation_rate",
                 "scale_forward_speed",
                 "scale_rotation_rate_",
                 "scale_forward_speed_",
                 "t"]:
        dot.node(node, node)

    dot.node("msg1", "msg")
    dot.node("msg2", "msg")

    dot.edge("scale_rotation_rate", "msg1")
    dot.edge("scale_forward_speed", "msg1")
    dot.edge("msg1", "/scale")

    dot.edge("/scale", "scale_rotation_rate_")
    dot.edge("/scale", "scale_forward_speed_")
    dot.edge("scale_rotation_rate_", "msg2")
    dot.edge("scale_forward_speed_", "msg2")
    dot.edge("t", "msg2")
    dot.edge("msg2", "/turtle2/cmd_vel")

    return dot

if __name__ == "__main__":
    dot = create_dot_file_ddfg()

    dot.render("ddfg.dot", view=False)
    dot.edge("/turtle2/cmd_vel", "t")
    dot.render("eddfg.dot", view=False)
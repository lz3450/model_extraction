import subprocess
import re
from graphviz import Digraph

EXCLUDED_TOPICS = ["/parameter_events", "/rosout"]


def run_ros2_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    return stdout, stderr


def get_ros2_nodes():
    stdout, stderr = run_ros2_command(["ros2", "node", "list"])
    if stderr:
        print("Error:", stderr)
        return []

    nodes = stdout.split('\n')[:-1]
    return nodes


def get_ros2_topics():
    stdout, stderr = run_ros2_command(["ros2", "topic", "list"])
    if stderr:
        print("Error:", stderr)
        return []

    topics = stdout.split('\n')[:-1]
    for _ in EXCLUDED_TOPICS:
        topics.remove(_)
    return topics


def get_ros2_node_info(node_name):
    stdout, _ = run_ros2_command(["ros2", "node", "info", node_name])
    node_info = stdout.split('\n')[:-1]
    return node_info


def parse_node_info(node_info):
    publishers = []
    subscribers = []
    for line in node_info:
        if "Publishers:" in line:
            mode = "publisher"
        elif "Subscribers:" in line:
            mode = "subscriber"
        elif "Service Servers:" in line:
            mode = "service_server"
        elif "Service Clients:" in line:
            mode = "service_client"
        elif "Action Servers:" in line:
            mode = "action_server"
        elif "Action Clients:" in line:
            mode = "action_client"
        elif line.startswith(" "):
            topic = re.sub(r'\s+', '', line)
            topic = topic.split(':', 1)[0]
            if mode == "publisher":
                if topic not in EXCLUDED_TOPICS:
                    publishers.append(topic)
            elif mode == "subscriber":
                if topic not in EXCLUDED_TOPICS:
                    subscribers.append(topic)

    return publishers, subscribers


def create_dot_file(nodes: list, topic_connections: dict):
    dot = Digraph("ROS2 Nodes and Topics", format="dot")
    dot.attr(rankdir="LR")

    for node in nodes:
        dot.node(node, node)

    for topic in topic_connections:
        dot.node(topic, topic, shape="rectangle")

        for pub in topic_connections[topic]['pub']:
            dot.edge(pub, topic)

        for sub in topic_connections[topic]['sub']:
            dot.edge(topic, sub)

    return dot


# def create_dot_file_scaler_publisher():
#     dot = Digraph("Scaler Publisher Dataflow", format="dot")
#     dot.attr(rankdir="LR")

#     for node in ["scale_rotation_rate", "scale_forward_speed"]:
#         dot.node(node, node, shape="diamond")

#     for node in ["msg"]:
#         dot.node(node, node)

#     for node in ["/scale"]:
#         dot.node(node, node, shape="rectangle")

#     dot.edge("scale_rotation_rate", "msg")
#     dot.edge("scale_forward_speed", "msg")
#     dot.edge("msg", "/scale")

#     return dot

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
    nodes = get_ros2_nodes()
    topics = get_ros2_topics()
    topic_connections = {topic: {"pub": set(), "sub": set()} for topic in topics}

    for node in nodes:
        node_info = get_ros2_node_info(node)
        publishers, subscribers = parse_node_info(node_info)

        for pub in publishers:
            topic_connections[pub]['pub'].add(node)

        for sub in subscribers:
            topic_connections[sub]['sub'].add(node)

    dot = create_dot_file(nodes, topic_connections)
    dot.render("ros2_nodes_topics.dot", view=False)

    dot = create_dot_file_ddfg()
    dot.render("ddfg.dot", view=False)
    dot.edge("/turtle2/cmd_vel", "t")
    dot.render("eddfg.dot", view=False)

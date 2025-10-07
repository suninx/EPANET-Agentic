import wntr
from typing_extensions import Annotated
from typing import List, Dict, Union
import pickle
import os
import re
import networkx as nx



# ------------- add control rules to .inp file --------------
def add_multiple_controls(
        inp_file: Annotated[str, "Network .inp file path"],

        multi_control_list: Annotated[
            List[Dict[str, Union[str, List[Dict[str, Union[str, int, float]]]]]],
            '''List of control definitions. Each item is a dict containing:

            - 'link_action_list': List of link actions. Each action dict requires:
                * 'element_name' (str): Link ID in the network.
                * 'action' (str or float): Either 'open', 'close', or a numeric setting.
                Example:
                [{'element_name': '330', 'action': 'open'}, {'element_name': '331', 'action': 25.0}]

            - 'condition_list': List of conditions. Each dict specifies a condition:
                * type (str): Either 'time' or 'value'
                * If 'time': requires:
                    - 'time_seconds' (int): Time when the control should be triggered, in seconds.
                    - 'relation' (str): e.g., 'is', 'not', 'after', 'before', 'greater_equal', 'less_equal'
                    - 'repeat' (float): default=0. If True, then repeat every 24-hours; if non-zero float, reset the
                                                condition every `repeat` seconds after the first_time.
                    - 'first_time' (float): default=0, Start rule at `first_time`, using that time as 0 for the condition evaluation
                * If 'value': requires:
                    - 'monitor_name' (str): Node or link to monitor
                    - 'attribute' (str): e.g., 'pressure', 'demand', 'flow'
                    - 'operator' (str): e.g., '>', '<=', '=='
                    - 'value' (float): threshold value
                Example:
                [{'type': 'time', 'time_seconds': 3600, 'relation':'is', 'repeat':0, 'first_time':0}, 
                 {'type': 'value', 'monitor_name': '1', 'attribute': 'pressure', 'operator': '>', 'value': 46.0}]

            - 'logic' (optional str): Logic between multiple conditions. Can be 'AND' or 'OR'. Default is 'AND'.
            '''
        ],

) -> str:
    wn = wntr.network.WaterNetworkModel('code_dir/' + inp_file)

    for idx, control_def in enumerate(multi_control_list):
        link_action_list = control_def.get('link_action_list', [])
        condition_list = control_def.get('condition_list', [])
        logic = control_def.get('logic', 'AND')

        # parsing actions
        ctrl_actions = []
        for la in link_action_list:
            element_name = la['element_name']
            action = la['action']
            if action == 'open':
                act_value, act_attr = 1, 'status'
            elif action == 'close':
                act_value, act_attr = 0, 'status'
            elif isinstance(action, (int, float)):
                act_value, act_attr = action, 'setting'
            else:
                raise ValueError("Unsupported action.")
            ctrl_actions.append(wntr.network.controls.ControlAction(wn.get_link(element_name), act_attr, act_value))

        # parsing conditions
        conditions = []
        for cond in condition_list:
            if cond['type'] == 'time':
                threshold = cond['time_seconds']
                relation = cond.get('relation', 'is')
                repeat = cond.get('repeat', False)
                first_time = cond.get('first_time', 0)
                c = wntr.network.controls.SimTimeCondition(
                    model=wn,
                    relation=relation,
                    threshold=threshold,
                    repeat=repeat,
                    first_time=first_time
                )
            elif cond['type'] == 'value':
                monitor_name, attr, op, val = cond['monitor_name'], cond['attribute'], cond['operator'], cond['value']
                if attr in ['pressure', 'demand']:
                    c = wntr.network.controls.ValueCondition(wn.get_node(monitor_name), attr, op, val)
                elif attr == 'flow':
                    c = wntr.network.controls.ValueCondition(wn.get_link(monitor_name), attr, op, val)
                else:
                    raise ValueError("Unsupported attribute.")
            else:
                raise ValueError("Unsupported condition type.")
            conditions.append(c)

        ctrl_name = f"control_{idx}_{'_'.join([la['element_name'] for la in link_action_list])}"

        # determine whether it is a Rule
        if len(ctrl_actions) > 1 or len(conditions) > 1:
            final_condition = conditions[0]
            for c in conditions[1:]:
                final_condition = (wntr.network.controls.AndCondition if logic.upper() == 'AND'
                                   else wntr.network.controls.OrCondition)(final_condition, c)
            rule = wntr.network.controls.Rule(final_condition, ctrl_actions, name=ctrl_name)
            wn.add_control(ctrl_name, rule)
        else:
            ctrl = wntr.network.controls.Control(conditions[0], ctrl_actions[0], name=ctrl_name)
            wn.add_control(ctrl_name, ctrl)

    with open('code_dir/control_wn.pickle', 'wb') as f:
        pickle.dump(wn, f)

    return f'All controls have been added to the WDN in WDN (an wntr.network.model.WaterNetworkModel object) and saved as "control_wn.pickle", please use "control_wn.pickle".'



# ------------- add special scenarios to .inp file --------------
def apply_disaster_scenario(
    inp_file: Annotated[str, "Path to the EPANET .inp file"],
    disaster_list: Annotated[
        List[Dict[str, Union[str, Dict, List]]],
        '''List of disaster definitions. Each dict must include:
        - 'disaster_type': str, one of ['earthquake', 'leak', 'power_outage', 'fire', 'contamination', 'chemical_booster']
        - 'params': parameters for the disaster, format depends on disaster_type:
            * earthquake:
                {
                    'epicenter': Tuple(float, float),
                    'magnitude': float,
                    'depth': float,
                    'indicate': 'pga' | 'pgv'
                }
            * leak:
                [
                    {'link_name': str, 'area': float, 'start_time': int (optional), 'end_time': int (optional)}
                ]
            * power_outage:
                [
                    {'link_name': str, 'start_time': int (optional), 'end_time': int (optional)}
                ]
            * fire:
                [
                    {'node_name': str, 'fire_flow_demand': float, 'fire_start': int (optional), 'fire_end': int (optional)}
                ]
            * contamination:
                {
                    'trace_nodes': List[str]
                }
            * chemical_booster:
            [
                {
                    'node_name': str,                # Node where the chemical is injected
                    'booster_start': int (optional), # Start time in seconds
                    'booster_end': int (optional),   # End time in seconds
                    'source_type': str (optional),   # One of 'SETPOINT', 'CONCEN', 'MASS', 'FLOWPACED'
                                                     #  - 'CONCEN'    : Injects a specific concentration at the node
                                                     #  - 'MASS'      : Fixed mass flow rate is injected
                                                     #  - 'FLOWPACED' : Maintains fixed concentration at the **inflow** of the node
                                                     #  - 'SETPOINT'  : Maintains fixed concentration at the **outflow** of the node
                    'quality': float (optional)      # Strength of the source (mass/time or mass/volume depending on type)
                }
            ]
        Example:
        [
            {'disaster_type': 'earthquake', 'params': {'epicenter': (0,0), 'magnitude': 5.5, 'depth': 10, 'indicate': 'pga'}},
            {'disaster_type': 'leak', 'params': [{'link_name': '123', 'area': 0.05}]}
        ]
        '''
    ],
    save_name: Annotated[str, "Filename to save the resulting WDN model or earthquake data (e.g., 'scenario.pickle')"]
) -> str:


    def ensure_nonempty_str(d: dict, key: str, context: str = '') -> str:
        value = d.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid '{key}' in {context}")
        return value

    wn = wntr.network.WaterNetworkModel('code_dir/' + inp_file)
    earthquake_data = None

    for disaster in disaster_list:
        disaster_type = ensure_nonempty_str(disaster, 'disaster_type', 'disaster definition')
        params = disaster.get('params')

        if disaster_type == 'earthquake':
            if not isinstance(params, dict):
                raise ValueError("'params' must be a dict for earthquake disasters.")

            indicate = ensure_nonempty_str(params, 'indicate', 'earthquake')
            if indicate not in ['pga', 'pgv']:
                raise ValueError("indicate must be 'pga' or 'pgv'.")

            epicenter = params.get('epicenter')
            magnitude = params.get('magnitude')
            depth = params.get('depth')

            if len(epicenter) != 2:
                raise ValueError("'epicenter' must be a tuple of (x, y).")
            if not isinstance(magnitude, (int, float)):
                raise ValueError("'magnitude' must be a number.")
            if not isinstance(depth, (int, float)):
                raise ValueError("'depth' must be a number.")

            earthquake_data = f'"earthquake_{indicate}.png" and "earthquake_repair.png" have been both saved, Please use DataAnalyzer to do analysis'
            wn = wntr.morph.scale_node_coordinates(wn, 1000)
            earthquake = wntr.scenario.Earthquake(epicenter, magnitude, depth)
            distance = earthquake.distance_to_epicenter(wn, element_type=wntr.network.Pipe)

            if indicate == 'pga':
                value = earthquake.pga_attenuation_model(distance)
                wntr.graphics.plot_network(wn, link_attribute=value, node_size=4, link_width=2,
                                           link_colorbar_label='PGA (g)',
                                           filename='code_dir/earthquake_pga.png')
            else:
                value = earthquake.pgv_attenuation_model(distance)
                wntr.graphics.plot_network(wn, link_attribute=value, node_size=4, link_width=2,
                                           link_colorbar_label='PGV (m/s)',
                                           filename='code_dir/earthquake_pgv.png')

            repair_rate = earthquake.repair_rate_model(value)
            wntr.graphics.plot_network(wn, link_attribute=repair_rate, node_size=4, link_width=2,
                                       link_colorbar_label='number of repairs per m',
                                       filename='code_dir/earthquake_repair.png')

        elif disaster_type == 'leak':
            if not isinstance(params, list):
                raise ValueError("Leak disaster expects params as a list of leak definitions.")
            for leak in params:
                pipe_name = ensure_nonempty_str(leak, 'link_name', 'leak')
                area = leak.get('area')
                if not isinstance(area, (int, float)):
                    raise ValueError("'area' must be a number in leak definition.")
                start_time = leak.get('start_time', 0)
                end_time = leak.get('end_time', 24 * 3600)

                leak_node_name = f"{pipe_name}_leak_node"
                wn = wntr.morph.split_pipe(wn, pipe_name, f"{pipe_name}_B", leak_node_name)
                leak_node = wn.get_node(leak_node_name)
                leak_node.add_leak(wn, area=area, start_time=start_time, end_time=end_time)

        elif disaster_type == 'power_outage':
            if not isinstance(params, list):
                raise ValueError("Power outage disaster expects params as a list.")
            for outage in params:
                pump_name = ensure_nonempty_str(outage, 'link_name', 'power outage')
                start_time = outage.get('start_time', 0)
                end_time = outage.get('end_time', 24 * 3600)
                pump = wn.get_link(pump_name)
                if pump is None:
                    raise ValueError(f"Pump '{pump_name}' not found in the network.")
                pump.add_outage(wn, start_time, end_time)

        elif disaster_type == 'fire':
            if not isinstance(params, list):
                raise ValueError("Fire disaster expects params as a list.")
            for fire in params:
                node_name = ensure_nonempty_str(fire, 'node_name', 'fire')
                fire_flow_demand = fire.get('fire_flow_demand')
                if not isinstance(fire_flow_demand, (int, float)):
                    raise ValueError("'fire_flow_demand' must be a number.")
                fire_start = fire.get('fire_start', 0)
                fire_end = fire.get('fire_end', 24 * 3600)
                node = wn.get_node(node_name)
                if node is None:
                    raise ValueError(f"Node '{node_name}' not found in the network.")
                node.add_fire_fighting_demand(wn, fire_flow_demand, fire_start, fire_end)

        elif disaster_type == 'contamination':
            if not isinstance(params, dict):
                raise ValueError("Contamination disaster expects params as a dict.")
            trace_nodes = params.get('trace_nodes')
            if not isinstance(trace_nodes, list) or not trace_nodes or not all(isinstance(n, str) and n.strip() for n in trace_nodes):
                raise ValueError("'trace_nodes' must be a non-empty list of non-empty strings.")
            for node_name in trace_nodes:
                if wn.get_node(node_name) is None:
                    raise ValueError(f"Trace node '{node_name}' not found in the network.")
            wn.options.quality.parameter = 'TRACE'
            wn.options.quality.trace_node = trace_nodes[-1]

        elif disaster_type == 'chemical_booster':
            if not isinstance(params, list):
                raise ValueError("Chemical booster disaster expects params as a list.")
            wn.options.quality.parameter = 'CHEMICAL'
            for i, booster in enumerate(params):
                node_name = ensure_nonempty_str(booster, 'node_name', 'chemical booster')
                booster_start = booster.get('booster_start', 0)
                booster_end = booster.get('booster_end', 24 * 3600)
                source_type = booster.get('source_type', 'SETPOINT')
                if source_type not in ['SETPOINT', 'CONCEN', 'MASS', 'FLOWPACED']:
                    raise ValueError(f"Invalid source_type '{source_type}' in chemical booster.")
                quality = booster.get('quality', 1000)
                if not isinstance(quality, (int, float)):
                    raise ValueError("'quality' must be a number in chemical booster.")

                pattern_name = f'SourcePattern_{i}'
                source_name = f'Source_{i}'
                source_pattern = wntr.network.elements.Pattern.binary_pattern(
                    pattern_name,
                    start_time=booster_start,
                    end_time=booster_end,
                    duration=wn.options.time.duration,
                    step_size=wn.options.time.pattern_timestep
                )
                wn.add_pattern(pattern_name, source_pattern)
                wn.add_source(source_name, node_name, source_type, quality, pattern_name)

        else:
            raise ValueError("Unsupported disaster type. Use 'earthquake', 'leak', 'power_outage', 'fire', 'contamination', or 'chemical_booster'.")

    save_path = f'code_dir/{save_name}'
    if earthquake_data is not None and len(disaster_list) == 1:
        return earthquake_data
    else:
        with open(save_path, 'wb') as f:
            pickle.dump(wn, f)
            f.close()
            return f"Disasters have been applied in WDN in an object of the wntr.network.model.WaterNetworkModel class that has saved in '{save_name}', please use '{save_name}' to do simulation"



# ------------- check .inp file --------------
def is_runnable_inp(
    inp_file: Annotated[
        str,
        "Path to the EPANET .inp file. The tool will check whether this file can be loaded and successfully simulated without error."
    ],
task_elements: Annotated[
        Dict[str, Union[List[str], List[int]]],
        """
        Optional: Task description dictionary. May include:
        - 'nodes': List of node IDs to check existence.
        - 'links': List of link IDs to check existence.
        - 'times': List of times (in seconds) to check if within simulation duration.
        """
    ] = None
) -> str:
    if not os.path.exists('code_dir/'+inp_file):
        return f"❌ File not found: {inp_file}"

    try:
        wn = wntr.network.WaterNetworkModel('code_dir/'+inp_file)
        duration = wn.options.time.duration

        num_junctions = len(wn.junction_name_list)
        num_pipes = len(wn.pipe_name_list)
        num_pumps = len(wn.pump_name_list)
        num_valves = len(wn.valve_name_list)
        num_tanks = len(wn.tank_name_list)
        num_reservoirs = len(wn.reservoir_name_list)

        G = wn.to_graph()  # directed multigraph
        uG = G.to_undirected()  # undirected multigraph
        link_density = nx.density(G)
        central_point_dominance = wntr.metrics.central_point_dominance(G)
        try:
            ave_shortest_path_length = nx.average_shortest_path_length(uG)
        except nx.NetworkXError:
            num_components = nx.number_connected_components(uG)
            return (
                f"✅ INP file is valid and simulation ran successfully.\n"
                f"The network contains {num_junctions} junctions, {num_pipes} pipes, "
                f"{num_pumps} pumps, {num_valves} valves, {num_tanks} tanks, and {num_reservoirs} reservoirs.\n"
                f"Graph metrics: link density = {link_density:.4f}, "
                f"central point dominance = {central_point_dominance:.4f}, "
                f"❗Average shortest path length could not be computed because the graph contains {num_components} disconnected subgraphs; "
                f"eccentricity was deliberately skipped because it requires a connected graph. Please check the network for unconnected nodes or isolated components.")
    except Exception as e:
        return f"❌ Failed to load INP file: {e}"

    try:
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()
    except Exception as e:
        return f"❌ Simulation failed: {e}"

    if task_elements:
        invalid_nodes = []
        invalid_links = []
        out_of_bounds_times = []

        if "nodes" in task_elements:
            invalid_nodes = [n for n in task_elements["nodes"] if n not in wn.node_name_list]
        if "links" in task_elements:
            invalid_links = [l for l in task_elements["links"] if l not in wn.link_name_list]
        if "times" in task_elements:
            out_of_bounds_times = [t for t in task_elements["times"] if t > duration]

        if invalid_nodes:
            return f"❌ Task error: The following node(s) not found in the network: {invalid_nodes}"
        if invalid_links:
            return f"❌ Task error: The following link(s) not found in the network: {invalid_links}"
        if out_of_bounds_times:
            return f"❌ Task error: The following time(s) exceed simulation duration ({duration}s): {out_of_bounds_times}"

    if results.node is None or results.link is None:
        return "⚠️ Simulation ran but results are missing (node/link is None)."

    try:
        all_node_nan = all(df.isnull().all().all() for df in results.node.values())
        all_link_nan = all(df.isnull().all().all() for df in results.link.values())
    except Exception as e:
        return f"⚠️ Simulation completed, but result parsing failed: {e}"

    if all_node_nan or all_link_nan:
        return "⚠️ Simulation completed, but all results are NaN (check network logic or simulation settings)."

    return (
        f"✅ INP file is valid and simulation ran successfully.\n"
        f"The network contains {num_junctions} junctions, {num_pipes} pipes, "
        f"{num_pumps} pumps, {num_valves} valves, {num_tanks} tanks, and {num_reservoirs} reservoirs.\n"
        f"Graph metrics: link density = {link_density:.4f}, "
        f"central point dominance = {central_point_dominance:.4f}, "
        f"average shortest path length = {ave_shortest_path_length:.2f}."
    )



# ------------- format conversion --------------
def parse_and_convert_to_markdown(txt_path, md_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    md_lines = ["### ✅ Conversation Log: EPANET-GPT Interaction\n"]

    role_map = {
        "TextMessage (user)": "user",
        "TextMessage (Orchestrator)": "Orchestrator",
        "TextMessage (TaskExecutor)": "TaskExecutor",
        "TextMessage (CodeRunner)": "CodeRunner",
        "TextMessage (DataAnalyzer)": "DataAnalyzer",
        "ToolCallRequestEvent": "TOOL CALL",
        "ToolCallExecutionEvent": "TOOL RESULT",
        "ToolCallSummaryMessage": "TOOL SUMMARY",
        "UserInputRequestedEvent": "user"
    }

    current_role = None
    buffer = []

    def flush_buffer():
        if current_role and buffer:
            content = ''.join(buffer).strip()
            if current_role == "TOOL CALL":
                md_lines.append(f"\n**Tool Call**:\n```json\n{content}\n```\n")
            elif current_role == "TOOL RESULT":
                md_lines.append(f"\n**Tool Result**:\n```\n{content}\n```\n")
            elif current_role == "TOOL SUMMARY":
                md_lines.append(f"\n**Tool Summary**:\n```\n{content}\n```\n")
            else:
                md_lines.append(f"\n**{current_role}** said:\n```\n{content}\n```\n")
        buffer.clear()

    for line in lines:
        role_match = re.match(r'^-+ (.+?) -+\n$', line)
        if role_match:
            flush_buffer()
            role_raw = role_match.group(1).strip()
            current_role = role_map.get(role_raw, role_raw)
        else:
            buffer.append(line)

    flush_buffer()
    md_lines.append("\n---\n✅ Conversation Ended\n")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.writelines(md_lines)

    print(f"[✓] Converted {txt_path} → {md_path}")



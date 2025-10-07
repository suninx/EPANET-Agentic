from autogen_agentchat.ui import Console
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent, CodeExecutorAgent
from llm import deepseekV3, deepseekR1, qwen
from autogen_agentchat.conditions import TextMentionTermination,  MaxMessageTermination
from tools import apply_disaster_scenario, add_multiple_controls, is_runnable_inp, parse_and_convert_to_markdown
from prompts import orchestrator_prompt, task_executor_prompt, coder_prompt
import json
from typing_extensions import Annotated
from typing import List
import PIL
from autogen_agentchat.messages import MultiModalMessage, TextMessage
from autogen_core import Image
import os




async def CodeRunner(message: Annotated[
    str, 'The message should provide a full description of the request regarding saving the data. For instance, "plot the data and save the plot as image"'],
                    WDN_status: Annotated[
                        str, "Path to the saved WDN data file (e.g., 'wn.pickle'), or an initialized WNTR WaterNetworkModel object (e.g., generated via wntr.network.WaterNetworkModel(inp_file)). The file should contain the complete network data or relevant simulation results to be used for plotting or saving as an image."],
                    name: Annotated[
                        str, 'a proper name for the file with a proper format (.png for image or .txt for data) to be saved.'],
                     ) -> str:
    coder_user = CodeExecutorAgent("coder_user",
                                   code_executor=LocalCommandLineCodeExecutor(work_dir="code_dir", timeout=120))

    coder = AssistantAgent(
        name="coder",
        system_message=coder_prompt,
        model_client=deepseekR1,
    )
    text_termination = TextMentionTermination(text="===TASK DONE===",sources=['coder_user'])
    max_message_termination = MaxMessageTermination(20)
    termination = text_termination | max_message_termination

    agent_team = RoundRobinGroupChat(participants=[coder, coder_user], termination_condition=termination,
                                     max_turns=20)

    stream = agent_team.run_stream(task=f'task: {message}\nname of file to be saved: {name}\nWDN status:{WDN_status}')
    results = await Console(stream)

    return results.messages[-2].content,results.messages[-1].content


async def DataAnalyzer(
    message: Annotated[str, '''The natural language request or query that describes what the assistant should analyze or explain about the image(s) or result documents. 
                                For example, "Describe the PGA distribution in the first image and compare it with the second image", 
                                "What is the difference between these two plots?" or
                                "Based on the original task, summarize the findings from the result file"'''],
    paths: Annotated[List[str], "A list of one or more file paths to images or .txt files that will be analyzed."]
) -> str:

    multi_model_agent = AssistantAgent(
        name="multi_model_agent",
        model_client=qwen,
        system_message="You extract important information from plots or texts."
    )

    image_objs = []
    text_contents = []

    for path in paths:
        ext = os.path.splitext(path)[-1].lower()

        try:
            if ext in [".txt", ".json"]:
                with open('code_dir/'+path, "r", encoding="utf-8") as f:
                    text_contents.append(f.read())
            elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                image_objs.append(Image(PIL.Image.open('code_dir/'+path)))
        except Exception as e:
            return f"Failed to load {path}: {e}"


    full_content = [message]
    if text_contents:
        full_content.append("\n\n".join(text_contents))
    full_content += image_objs


    if image_objs:
        task_message = MultiModalMessage(content=full_content, source="user")
    else:
        task_message = TextMessage(content="\n\n".join(full_content), source="user")

    team = RoundRobinGroupChat(participants=[multi_model_agent], max_turns=1)
    stream = team.run_stream(task=task_message)
    result = await Console(stream)

    return [msg.content for msg in result.messages]





async def TaskExecutor(message: Annotated[str, 'A detailed description of the task involving control rule addition or disaster scenario simulation for a water distribution network. For example: "Add a control rule to open valve V1 if tank T1 level drops below 40", or "Simulate a leak at pipe P103 from hour 1 to 5".'],
                     path: Annotated[str,'Path to the WDN file (.inp)']):

    TaskExecutor = AssistantAgent(
        name="TaskExecutor",
        model_client=deepseekV3,
        system_message=task_executor_prompt,
        tools=[add_multiple_controls, apply_disaster_scenario, is_runnable_inp],
        reflect_on_tool_use=True,
    )

    team = RoundRobinGroupChat(participants=[TaskExecutor], max_turns=1)
    stream = team.run_stream(task=f'task: {message}\npath of the file: {path}')
    result = await Console(stream)

    return [msg.content for msg in result.messages]



async def main(task_description):

    user = UserProxyAgent('user', input_func=input)
    orchestrator = AssistantAgent(
        name="Orchestrator",
        system_message=orchestrator_prompt,
        model_client=deepseekV3,
        tools=[TaskExecutor, CodeRunner, DataAnalyzer])

    termination = MaxMessageTermination(30) | TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat(participants=[orchestrator, user], termination_condition=termination,
                               max_turns=30)

    stream = team.run_stream(task=task_description)
    await Console(stream)




if __name__ == "__main__":

    with open('tasks/manuscript.json', 'r') as f:
        tasks = json.load(f)
    task_description = tasks[8]['description']
    task_id = tasks[8]['task_id']
    # input = tasks[6]['input']
    # parse_and_convert_to_markdown('conversation/save.txt', f"conversation/test/manuscript/Scenario simulation/{task_id}.md")
    asyncio.run(main(task_description))



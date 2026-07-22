# Article Scaffolding
## The Case for Browser Agents
Urban planners are now using browser agents for their workflows.
https://www.linkedin.com/feed/update/urn:li:activity:7481285576047063041/
Nick Williamson an urban planner and civil service innovator, using sophisticated AI workflows for his personal life.
From a deeper conversation with Nick I can confidently extrapolate that this workflow extends beyond a personal toy project but to represent a feasible trajectory for applying AI to civil-service and urban-planning work: fields that often use substantial amounts of data but have traditionally relied on relatively conventional methods of gathering, analysing, and synthesising it.

What is the consequence of this movement? Allow me to describe with the following logic:

1. Increase adoption of general non-technical consumer facing products like Claude Cowork and now ChatGPT Work (same thing different providers, its just a remote computer workspace designed for an LLM agent to control, in effect having a super intelligent computer wiz on call)
2. The general non-technical consumer does not care (or even know) about APIs or programming, they just want to get value from a tool using the GUI.
3. The tools have no demand to justify exposing the API.
4. LLM agents has no means to interact with the tool... 
5. The LLM agents must resort to using the browser themselves. Hence browser agents being dispropotionately adopted by the general non-technical consumer!

## Limits of Browser Agents
Browser agents in premise are fantastic untill you kick one off, wait 60 seconds for it to begin, 10 seconds to scroll down, another 10 seconds to scroll again, finally clicks to navigate somewhere...
At which point you cancel the task and do it yourself.
Or you just leave it running hoping it does the right thing, come back 30 minutes later to find it failed, or worst case, it did the wrong thing and took actions you have to correct or cannot even revert.

The browser agent's failure modes can be destructured into the following:
1. Latency: it is too slow to maintain the user's attention
2. Efficiency: it takes several more turns than a human would, introducing risk of adverse effects in the state of the target system.  
3. Correctness: The browser agent may fail to complete the task.

I explored a series of methods to unilaterally improve accross each of these axes against a clean room version of Claude in Chrome.
The expectation was that any naive method would be sufficient to improve accross all three axes, this was not the case, but with the right methodology I discovered that you can significantly improve accross all axes. This is the story of this experimentation and discovery.

## Study setup

### Dataset
The study begins with the dataset.
The dataset used is a stratified subset sourced from the REAL web-agent benchmark.
The REAL dataset consists of 112 tasks designed to run against 11 target sites.
The study focused on 2 sites, "dashdish" (DoorDash clone) and "zilloft" (Zillow clone) on the basis that each had enough easy/medium and hard tasks to get a large enough sample size to both train and test on.
Each side with a total of 7 easy/medium tasks and 2 hard tasks.
Three medium tasks were randomly selected from each target site to build the train set.
The remaining 12 composed the held-out test set.

Caveat:
Although REAL provides difficulty labels for each task they were quickly saturated by the study baseline.

The target sites store their state in the sites cache and each site must follow a specific configuration to setup the task. Then an actor runs against the site. Finally the state of the site is captured and then scored against REAL's evaluation script.

### Factors
For each arm of the study, we phased in different factors and measured their impact across the three axes.
Each factor is defined as follows and is accompanied by a pictoral metaphor to help illustrate the concept.

#### Harness
The key factor from which this whole study is built is the harness.
The harness has 2 levels the official closed source Anthropic harness Claude in Chrome (CinC) and an augmented clean room version aptly named open-claude-in-chrome (OCIC).
Why make a clean room version? Three reasons:
1. Claude in Crhome controls which sites you have access to, this significantly limits the degrees of freedom of Claude resulting in people building unecessary companies from this limitation.
2. Claude in Chrome limits the extension to only work on Chrome and Edge, if you use a different browser you are out of luck.
3. Claude in Chrome harness uses several methods that slow down the agent and may decrease performance in other axes, that is completely out the user's control.

OCIC solves each of these problems in turn expanding utility and improving performance by design, resulting in a roughly .1s improvement per round trip call.

There is only a signle arm that uses CinC, it serves as the control group for the study.

IMAGE OF HARNESS FACTOR

CAPTION: The harness is represented by the forehead branding on the character's forehead.

#### Browser
The browser is the substrate within which the agent operates, similar to the harness, this contains two levels: Chrome and Brave.

There is only two arms that use the Chrome browser, the rest use Brave.

IMAGE OF BROWSER FACTOR

CAPTION: This factor is representated as the table the student to do their work on.

#### Context Load
This factor is tremendously influential, as it wholistically dictates the latency of inference. Context load represents the amount of context already loaded into the claude run session in an arm before the task is kicked off.

IMAGE OF CONTEXT LOAD FACTOR BESIDES THE INTERNALIZED PRIOR

CAPTION: The context load is represented by the apparent tiredness of the student and a though bubble. This representation is more direct than many of the other factors as they have a monotonic relationship. If you study more hours and you are tired you are likely to perform worse; If you load more context in the session the inference latency will increase.The though bubble accompanies the tireness to visualize the internalized material that was loaded into the context.


#### Source
The source represents the kind of trajectory format. In our case we have two levels: self generated and expert demonstrations.
Self generated or experiential trajectory represents the agent's own attempts at solving the train set of tasks.
Expert demonstrations are captured via a new feature to OCIC in session recordings. These recordings capture several types data simultaneously including: behavioral actions, cognitive transcripts, and cursor movements.

IMAGE OF SOURCE FACTOR

CAPTION: The experiential is represented by completed tasks showcasing the agent's prior attempts at solving similar problems. Alternatively the expert demonstration are represented as a book illustrating an experts recollection of their attempts at solving similar problems.

#### Compression Delivery
In some instances we perform an analysis of the sources in essense compressing them. The compression is then delivered in two ways. First as an independent document added to the workspace. Second is as an artifact appended to the task prompt.

IMAGE OF COMPRESSION DELIVERY FACTOR

CAPTION: The compression is represented either by an analysis document often times sitting atop the source material or as a box inside the task paper an analog to reference material to an exam.

### Study Arms
The study is motivated by personal experience building methods to drive better performance in browser agents.
I never formally studied the impact of these methods instead I relied on intuition.
The study is designed to investigate the impact of each of these methods in a controlled manner while ablating through levels to discover the atomic impact of each factor in the method.
#### Phase 1: Baseline
Baseline assessing the performance of the two harnesses.
##### 1a (CinC): CinC x Chrome
Claude in Chrome running in the stock Chrome Browser.

IMAGE OF 1A
##### 1b (OCIC-Ch): OCIC x Chrome
OCIC running in the stock Chrome Browser.

IMAGE OF 1B
##### 1c (OCIC-Br): OCIC x Brave
OCIC running in the Brave Browser.

IMAGE OF 1C
#### Phase 2: Sources in Workspace
Phase 2 is driven by the hypothesis that giving the agent access to similar trajectories in its workspace will drive better performance contingent on the agent seeking relevant information via agentic search.
##### 2a: OCIC x Brave x Experiential (workspace)
OCIC running in the Brave Browser with prior experience trajectories in its workspace (plus a readme for context on what exists in the workspace).

IMAGE OF 2A

##### 2b: OCIC x Brave x Expert (workspace)
OCIC running in the Brave Browser with prior expert trajectories in its workspace (plus a readme for context on what exists in the workspace).

IMAGE OF 2B

#### Phase 3: Analyzed Workspace Sources
Following up on the discovery of the reduced performance of phase 2 I hypothesized that providing an analysis of the sources would reduce the lookup time needed to build a model of the sites. Phase 3 is designed to test this hypothesis.
##### 3a: OCIC x Brave x Experiential (workspace) x Analysis Docs
OCIC running in the Brave Browser with prior experience trajectories in its workspace and an analysis document grounded on the prior sources already in the workspace (plus a readme for context on what exists in the workspace).

IMAGE OF 3A

##### 3b: OCIC x Brave x Expert (workspace) x Analysis Docs
OCIC running in the Brave Browser with prior expert demonstrations in its workspace and an analysis document grounded on the prior sources already in the workspace (plus a readme for context on what exists in the workspace).

IMAGE OF 3B

#### Phase 4: Context Loaded. Forks.
Building off the poor performance of phase 3 I learned that for the current difficulty of tasks the cost agentic search would not payoff. I hypothesized that instead of having the agent search through its workspace for priors you could naively reap the benefits of prior experience by loading the priors dirctly into context before running the task.  
##### 4a: OCIC x Brave x Experiential (context)
OCIC running in the Brave Browser with prior experience trajectories loaded into context naively by continuing the Claude session.

IMAGE OF 4A

##### 4b: OCIC x Brave x Expert (context)
OCIC running in the Brave Browser with prior expert demonstrations internalized ahead of the task by performing a deep analysis of the expert demonstrations. Unlike 4a there is no means of loading the context naively so instead the agent internalized the context by operating on a workspace that contains the expert demonstrations. Over the course of internalizing the content the agent wrote notes onto disk which we represent as analysis documents.

IMAGE OF 4B

#### Phase 5: Prompt Embedded Analysis 
Phase 4 helped me reminded me of a mechanic of LLMs where put simply more context results in higher latency. Drawing from that and prior phases I hypothesized that if the content of the experiences is distilled and embedded into the task prompt then the agent can reap the benefits of prior experience without the cost of agentic search nor the buildup of context.
For both arms of this phase the analysis artifacts are constructed by distilling both 6 expert demonstrations and 6 experience trajectories.
##### 5a: OCIC x Brave x Single Analysis Embedded Task
OCIC running in the Brave Browser with a single analysis artifact embedded into the task prompt. 

IMAGE OF 5A

##### 5b: OCIC x Brave x Dynamic Analysis Embedded Task
OCIC running in the Brave Browser with a single analysis artifact embedded into the task prompt dynamically from a set of two total artefacts constructed.

IMAGE OF 5B

#### Phase 6: Warm-up Context Loaded
##### 6a: OCIC x Brave x Single Experiential (context)
##### 6b: OCIC x Brave x Single Analysis Embedded Task x Single Experiential (context)


## Solution
## Results




# Scientific Scaffolding
## Abstract
- continual learning with a focus on latency
- ablation study across each factory varying conditions


## Methodology
- expert demonstrations (teacher demonstrations maybe)
    - caveat that I am not an expert for the site nor task but I am a human with a good deal of experience with navigating and building websites
- self generated experiences
- distillation
- playbook or the more practical form, a skill
- procedural knowledge knowledge is how to and the recepie (grounded in cognitive science)
- declarative knowledge is facts about the site like the analysis doc (grounded in cognitive science)
- cold vs warm start grounded in model weights priming but its a good analogy for the session forks
- verification: llm as judge, programmatic/rule-based verifiers
- latency: e2e latency, wall-clock latency per task, per-turn latency
- stock chromium browsers: chrome, brave, opera, edge
    - driven by extension (can also be driven by CDP)
- automation chromium: what puppeteer, playwright, etc. do
    - driven by CDP
- observation space: browser(my profile)
- action space: browser(my profile) + env
- agentic search: filesystem based retrieval
- harness: OCIC
- workspace: on disk working directory
- target: browser site




## Dataset
- dataset is not specially hard but it is long enough to explore latency
- run to run variance: prebuilt verifiers are not consistent to semantically equivalent llm outputs
- held out train vs test split

## Limitations
- 0$ budget (self imposed)
    - the moment I open the budget to >0 then it rapidly gets expensive
- parallelizing the process is not trivial with the current configuration of OCIC
- 


# Notes
hypothesis:
information article is the takeaways from this experiment - i did xyz and here are the results
hypothesis:
we came in with this hypothesis 
a good article has a hypothesis that matters

we are exploring several axis: correctness, latency, and efficiency  

Hypothesis:
HIGHER LEVEL HYPOTHESES:
naive procedural and declarative knowledge improves on the baseline? False, it depends on difficulty of the task, length of prior context, and methodology of prior context
expert demonstrations produce a stronger world model than self generated experiences?
LOWER LEVEL HYPOTHESES:
more experience leads to lower latency? False, it results in lower turn turn count, but it necessarily leads to higher latency by design of transformer models.
more experience results in higher accuracy? unknown, the dataset is not challenging enough to test this hypothesis.
distilling prior experience results in lower latency? True, but by merit of decreased turn count per task with an upfront cost of agentic search

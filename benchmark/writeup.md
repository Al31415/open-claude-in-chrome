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

The key factor from which this whole study is built is the harness.
The harness has 2 levels the official closed source Anthropic harness Claude in Chrome and an augmented clean room version aptly named open-claude-in-chrome.
Why make a clean room version? Three reasons:
1. Claude in Crhome controls which sites you have access to, this significantly limits the degrees of freedom of Claude resulting in people building unecessary companies from this limitation.
2. Claude in Chrome limits the extension to only work on Chrome and Edge, if you use a different browser you are out of luck.
3. Claude in Chrome harness is not 

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

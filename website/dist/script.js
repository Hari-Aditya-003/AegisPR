const stages=[
  ["CONTEXT ENGINE","Repository structure before speculation.","AegisPR discovers the stack, changed files, commands, and dependency neighborhood. The Dell NVIDIA GPU ranks relevant context with deterministic CUDA vector scoring."],
  ["NEMOTRON REASONING","Risks written as testable hypotheses.","Nebius Token Factory serves NVIDIA Nemotron with bounded, untrusted repository context. Each hypothesis names an affected surface and a concrete verification strategy."],
  ["TEST SYNTHESIS","A claim becomes runnable code.","The planner produces framework-native tests and explicit commands. Only allowlisted commands reach the sandbox; prose can never become a shell instruction."],
  ["DIFFERENTIAL RUNNER","Same experiment. Two commits.","Isolated Docker sandboxes execute the generated check against the base and pull request revisions with no runtime network, dropped capabilities, and resource limits."],
  ["EVIDENCE REPORT","Conclusions constrained by outcomes.","A deterministic matrix classifies the result and stores commit SHAs, commands, exit codes, logs, durations, generated test code, and the scope disclaimer."]
];
document.querySelectorAll(".stage").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll(".stage").forEach(stage=>stage.classList.remove("active"));button.classList.add("active");const[label,title,copy]=stages[Number(button.dataset.stage)];document.querySelector("#stage-label").textContent=label;document.querySelector("#stage-title").textContent=title;document.querySelector("#stage-copy").textContent=copy;}));

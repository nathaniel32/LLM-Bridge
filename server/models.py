from pydantic import BaseModel
from typing import List, Optional
from common.models import Interaction
import json

class JobRequestError(Exception):
    pass

class ChatContext(BaseModel):
    system: Optional[str] = "You are a helpful assistant."
    interaction_history: List[Interaction] = []
    active_interaction: Optional[Interaction] = None

    def create_interaction(self, prompt):
        if self.active_interaction is not None:
            raise JobRequestError("Active interaction already exists")
        
        self.active_interaction = Interaction(prompt=prompt)
        self.interaction_history.append(self.active_interaction)

    def finish_interaction(self):
        self.active_interaction = None

    def edit_interaction(self, interaction_id, prompt):
        if self.active_interaction is not None:
            raise JobRequestError("Cannot edit while active interaction exists")
        
        self.active_interaction = next((i for i in self.interaction_history if i.id == interaction_id), None)
        if self.active_interaction is None:
            raise ValueError(f"Interaction with id {interaction_id} not found")

        self.active_interaction.prompt = prompt
        self.active_interaction.response = ""

    def remove_interaction(self, interaction_id) -> Interaction:        
        interaction = next((i for i in self.interaction_history if i.id == interaction_id), None)
        if interaction is None:
            raise ValueError(f"Interaction with id {interaction_id} not found")
        
        self.interaction_history.remove(interaction)
        
        if interaction is self.active_interaction:
            self.active_interaction = None

        interaction.prompt = ""
        interaction.response = ""

        return interaction
    
    def get_chat_message(self):
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        for interaction in self.interaction_history:
            messages.append({"role": "user", "content": interaction.prompt})
            if interaction is not self.active_interaction:
                messages.append({"role": "assistant", "content": interaction.response})
            else:
                break
        return json.dumps(messages)
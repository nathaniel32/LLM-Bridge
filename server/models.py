from pydantic import BaseModel
from typing import List, Optional
from common.models import Interaction
import json

class WaitingListError(Exception):
    pass

class ChatContext(BaseModel):
    system: Optional[str] = "You are a helpful assistant."
    interaction_history: List[Interaction] = []
    active_interaction: Optional[Interaction] = None

    def create_interaction(self, prompt):
        self.active_interaction = Interaction(prompt=prompt)
        self.interaction_history.append(self.active_interaction)

    def finish_interaction(self):
        self.active_interaction = None

    def edit_interaction(self, interaction_id, prompt):
        self.active_interaction = next((i for i in self.interaction_history if i.id == interaction_id), None)
        self.active_interaction.prompt = prompt
        self.active_interaction.response = ""
    
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
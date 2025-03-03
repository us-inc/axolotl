from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import torch


class ChatModel:
    def __init__(self, model_path):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype="auto", device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token  # Fix for pad_token_id warning

    def generate_response(self, prompt, max_tokens=1024):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text], return_tensors="pt", padding=True).to(self.model.device)

        streamer = TextStreamer(self.tokenizer)

        self.model.generate(
            **model_inputs, max_new_tokens=max_tokens, pad_token_id=self.tokenizer.eos_token_id, streamer=streamer
        )


if __name__ == '__main__':
    model = ChatModel("/shared/data/10k_test_final_model")
    while True:
        user = input("Enter: ")
        if user.lower() == "exit":
            break
        model.generate_response(user)

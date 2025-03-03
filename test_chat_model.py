from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class ChatModel:
    def __init__(self, model_path):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype="auto", device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

    def generate_response(self, prompt, max_tokens=1024):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs, max_new_tokens=max_tokens
        )

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response

if __name__ == '__main__':
    model = ChatModel("/shared/data/10k_test_final_model")
    user = input("Enter: ")
    while True:
        if user == "exit":
            break
        response = model.generate_response("Give me the value of 2+2")
        print(f"AI: {response}")

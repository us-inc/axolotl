import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer

def generate_response(model_path, prompt):
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype="auto", device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=4096
    )
    
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response

def main():
    parser = argparse.ArgumentParser(description="Generate a response using a chat model.")
    parser.add_argument("model_path", type=str, help="Path to the model directory")
    parser.add_argument("prompt", type=str, help="User prompt")
    
    args = parser.parse_args()
    
    response = generate_response(args.model_path, args.prompt)
    print("Response:", response)

if __name__ == "__main__":
    main()

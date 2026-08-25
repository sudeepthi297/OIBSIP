import random
import string

def generate_password(length, use_uppercase, use_numbers, use_symbols):
    character_pool = string.ascii_lowercase
    
    if use_uppercase:
        character_pool += string.ascii_uppercase
    if use_numbers:
        character_pool += string.digits
    if use_symbols:
        character_pool += string.punctuation

    # Fallback safety check
    if not character_pool:
        character_pool = string.ascii_lowercase

    selected_chars = random.choices(character_pool, k=length)
    return "".join(selected_chars)

def get_yes_no_input(prompt):
    """Helper function to cleanly ask a Yes/No question."""
    while True:
        response = input(prompt).strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def main():
    print("==========================================")
    print("   🔐 PYTHON PASSWORD GENERATOR (CLI)    ")
    print("==========================================\n")

    # 1. Get Password Length safely
    while True:
        try:
            length = int(input("Enter desired password length (e.g., 8-64): "))
            if length < 4:
                print("Passwords should be at least 4 characters long for basic security!")
                continue
            break
        except ValueError:
            print("Invalid input! Please enter a valid number.")

    # 2. Get Character Preferences
    use_uppercase = get_yes_no_input("Include uppercase letters? (y/n): ")
    use_numbers   = get_yes_no_input("Include numbers? (y/n): ")
    use_symbols   = get_yes_no_input("Include special symbols? (y/n): ")

    # Ensure at least one option is chosen
    if not (use_uppercase or use_numbers or use_symbols):
        print("\nNote: All options turned off. Defaulting to lowercase letters only.")

    # 3. Get Quantity of Passwords
    while True:
        try:
            count = int(input("\nHow many passwords would you like to generate? "))
            if count < 1:
                print("Please enter a number greater than 0.")
                continue
            break
        except ValueError:
            print("Invalid input! Please enter a valid number.")

    # 4. Generate and Output Passwords
    print("\n--- Your Generated Passwords ---")
    for idx in range(1, count + 1):
        password = generate_password(length, use_uppercase, use_numbers, use_symbols)
        print(f"[{idx}] {password}")
        
    print("\nDone! Stay safe online.")

if __name__ == "__main__":
    main()
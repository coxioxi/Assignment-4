# COMP 3200 -- Recursive-descent calculator 

import re
import sys

# --- lexer (lexical analyzer) ---
class Lexer:
    ignore = re.compile(r'[ \t]+')  # spaces and tabs

    rules = [
        (re.compile(r'==|!=|<=|>='), lambda s: s),
        (re.compile(r'[0-9]+'), lambda s: int(s)),                          # integer literals
        (re.compile(r'[a-zA-Z]+'), lambda s: s),                            # variables (letters only)
        (re.compile(r'[+\-*/^()?:|&!@%=<>%]'), lambda s: s),                # single-char operators and punctuation
        (re.compile(r'.'), lambda s: '#' + str(ord(s))),                    # any other single char -> error token
    ]

    def __init__(self, input_string):
        self.s = input_string
        self.pos = 0

    def next(self):
        # skip over ignorable characters
        m = self.ignore.match(self.s, self.pos)
        if m:
            self.pos = m.end()

        if self.pos >= len(self.s):
            return '$' # denotes end of input

        for r, f in self.rules:
            m = r.match(self.s, self.pos)
            if m:
                self.pos = m.end()
                return f(m.group())
        return '$'


# --- parse error ---
class ParseError(Exception):
    def __init__(self, message):
        self.message = message


# --- parser (recursive-descent) ---
class Parser:
    def __init__(self, input_string):
        self.lexer = Lexer(input_string)
        self.next()

    def next(self):
        self.tok = self.lexer.next()

    def error(self, msg):
        raise ParseError(msg + " [next token: " + str(self.tok) + "]")

    def parse(self):
        """ top-level parse: expression then end marker """
        e = self.parse_assign()    
        if self.tok == '$':
            return e
        else:
            self.error("extraneous input")

    # Assignment
    def parse_assign(self):
        e = self.parse_ternary()
        if isinstance(e, str) and e.isalpha() and self.tok == '=':
            self.next()
            rhs = self.parse_assign()
            return ('=', e, rhs)
        else:
            return e

    # Ternary
    def parse_ternary(self):
        e = self.parse_or()
        if self.tok == '?':
            self.next()
            true_branch = self.parse_assign()   # parse full expression
            if self.tok != ':':
                self.error("missing ':' in ternary expression")
            self.next()
            false_branch = self.parse_assign()
            return ('?:', e, true_branch, false_branch)
        return e

    # Or
    def parse_or(self):
        left = self.parse_and()
        if self.tok == '|':
            self.next()
            right = self.parse_or()
            return ('|', left, right)
        return left

    # And
    def parse_and(self):
        left = self.parse_not()
        if self.tok == '&':
            self.next()
            right = self.parse_and()
            return ('&', left, right)
        return left

    # Not
    def parse_not(self):
        if self.tok == '!':
            self.next()
            return ('!', self.parse_not())
        else:
            return self.parse_compare()

    # Compare
    def parse_compare(self):
        e = self.parse_add()
        while self.tok in ('==', '!=', '<', '<=', '>', '>='):
            op = self.tok
            self.next()
            right = self.parse_add()
            e = (op, e, right)
        return e

    # Add
    def parse_add(self):
        e = self.parse_mul()
        while self.tok in ('+', '-'):
            op = self.tok
            self.next()
            right = self.parse_mul()
            e = (op, e, right)
        return e

    # Mul
    def parse_mul(self):
        e = self.parse_unary()
        while self.tok in ('*', '/', '%'):
            op = self.tok
            self.next()
            right = self.parse_unary()
            e = (op, e, right)
        return e

    # Unary
    def parse_unary(self):
        if self.tok in ('-', '@'):
            op = self.tok
            self.next()
            return (op, self.parse_unary())
        else:
            return self.parse_pow()

    # Pow
    def parse_pow(self):
        left = self.parse_factor()
        if self.tok == '^':
            self.next()
            right = self.parse_pow()
            return ('^', left, right)
        return left

    # Factor 
    def parse_factor(self):
        if isinstance(self.tok, int):
            val = self.tok
            self.next()
            return val
        elif isinstance(self.tok, str) and self.tok.isalpha():
            name = self.tok
            self.next()
            return name
        elif self.tok == '(':
            self.next()
            e = self.parse_assign()
            if self.tok != ')':
                self.error("missing ')'")
            self.next()
            return e
        else:
            self.error("expected int, variable, or '('")


# --- evaluation (AST walker) ---

VARS = {}   # variable environment

def assign_var(name, value):
    VARS[name] = value
    return value

def eval(e):
    # integer literal
    if isinstance(e, int):
        return e

    # variable name
    if isinstance(e, str):
        return VARS.get(e, 0)

    # tuple node
    if isinstance(e, tuple):
        op = e[0]

        # Assignment
        if op == '=':
            varname = e[1]
            val = eval(e[2])
            return assign_var(varname, val)

        # Ternary
        if op == '?:':
            cond_val = eval(e[1])
            if cond_val != 0:
                return eval(e[2])
            else:
                return eval(e[3])

        # OR
        if op == '|':
            left_val = eval(e[1])
            if left_val != 0:
                return left_val
            return eval(e[2])

        # AND
        if op == '&':
            left_val = eval(e[1])
            if left_val == 0:
                return 0
            return eval(e[2])

        # Logical NOT
        if op == '!':
            return 1 if eval(e[1]) == 0 else 0

        # Unary minus
        if op == '-':
            return -eval(e[1])

        # Absolute
        if op == '@':
            return abs(eval(e[1]))

        # Binary arithmetic and comparison ops
        left = None
        right = None
        if len(e) >= 2:
            left = eval(e[1])
        if len(e) >= 3:
            right = eval(e[2])
        if op == '+':
            return left + right
        if op == '*':
            return left * right
        if op == '/':
            return left // right
        if op == '%':
            return left % right
        if op == '^':
            return left ** right

        # return 1 (true) or 0 (false)
        if op == '==':
            return 1 if left == right else 0
        if op == '!=':
            return 1 if left != right else 0
        if op == '<':
            return 1 if left < right else 0
        if op == '<=':
            return 1 if left <= right else 0
        if op == '>':
            return 1 if left > right else 0
        if op == '>=':
            return 1 if left >= right else 0

        # unknown operator
        raise ValueError(f"Unknown operator in eval: {op}")

    # invalid node
    raise ValueError("Invalid AST node for eval")


# --- wrapper to parse-and-eval a single line ---
def calc(line):
    ast = Parser(line).parse()
    return eval(ast)


# --- main: file-processing or REPL ---
def process_file(filename):
    try:
        with open(filename, 'r') as f:
            line_no = 0
            for raw in f:
                line_no += 1
                line = raw.strip()
                if not line:
                    continue
                try:
                    Parser(line)
                    result = calc(line)
                except ParseError as err:
                    print(f"{filename}:{line_no}: parse error: {err.message}")
                except Exception as ex:
                    print(f"{filename}:{line_no}: runtime error: {ex}")
    except FileNotFoundError:
        print(f"Error: cannot open file '{filename}'")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        filename = sys.argv[1]
        print(f"\n--- Processing file: {filename} ---")
        try:
            with open(filename) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    print(f"\nExpression: {line}")
                    try:
                        result = calc(line)
                        print("Result:", result)
                    except ParseError as err:
                        print("Parse error:", err.message)
            print("\nVariables:")
            for k, v in VARS.items():
                print(f"{k} = {v}")
        except FileNotFoundError:
            print(f"Error: file '{filename}' not found.")

    else:
        # interactive mode
        while True:
            try:
                line = input("calc> ")
            except EOFError:
                break

            if line.strip() == "":
                break

            try:
                e = Parser(line).parse()
                print("\tAST:", e)
                print(eval(e))
            except ParseError as err:
                print("Parse error:", err.message)


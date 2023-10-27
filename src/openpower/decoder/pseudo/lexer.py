# Based on GardenSnake - a parser generator demonstration program
# GardenSnake was released into the Public Domain by Andrew Dalke.

# Portions of this work are derived from Python's Grammar definition
# and may be covered under the Python copyright and license
#
#          Andrew Dalke / Dalke Scientific Software, LLC
#             30 August 2006 / Cape Town, South Africa

# Modifications for inclusion in PLY distribution
from copy import copy
from ply import lex
from openpower.decoder.selectable_int import SelectableInt


class SyntaxError2(Exception):
    """ class used to raise a syntax error but get ply to stop eating errors
    since it catches and discards SyntaxError after setting a flag.
    """

    def __init__(self, *args, cls=SyntaxError):
        super().__init__(*args)
        self.cls = cls

    def __repr__(self):
        return repr(self.cls(*self.args))

    def __str__(self):
        return str(self.cls(*self.args))

    def raise_syntax_error(self):
        raise self.cls(*self.args) from self


def raise_syntax_error(msg, filename, lineno, lexpos, input_text,
                       cls=SyntaxError):
    line_start = input_text.rfind('\n', 0, lexpos) + 1
    line_end = input_text.find('\n', line_start)
    col = (lexpos - line_start) + 1
    raise SyntaxError2(str(msg), (filename, lineno, col,
                                  input_text[line_start:line_end]), cls=cls)

# I implemented INDENT / DEDENT generation as a post-processing filter

# The original lex token stream contains WS and NEWLINE characters.
# WS will only occur before any other tokens on a line.

# I have three filters.  One tags tokens by adding two attributes.
# "must_indent" is True if the token must be indented from the
# previous code.  The other is "at_line_start" which is True for WS
# and the first non-WS/non-NEWLINE on a line.  It flags the check so
# see if the new line has changed indication level.

# Python's syntax has three INDENT states
#  0) no colon hence no need to indent
#  1) "if 1: go()" - simple statements have a COLON but no need for an indent
#  2) "if 1:\n  go()" - complex statements have a COLON NEWLINE and must indent
NO_INDENT = 0
MAY_INDENT = 1
MUST_INDENT = 2

# turn into python-like colon syntax from pseudo-code syntax.
# identify tokens which tell us whether a "hidden colon" is needed.
# this in turn means that track_tokens_filter "works" without needing
# complex grammar rules


def python_colonify(lexer, tokens):

    implied_colon_needed = False
    for token in tokens:
        #print ("track colon token", token, token.type)

        if token.type == 'THEN':
            # turn then into colon
            token.type = "COLON"
            yield token
        elif token.type == 'ELSE':
            yield token
            token = copy(token)
            token.type = "COLON"
            yield token
        elif token.type in ['DO', 'WHILE', 'FOR', 'SWITCH']:
            implied_colon_needed = True
            yield token
        elif token.type == 'NEWLINE':
            if implied_colon_needed:
                ctok = copy(token)
                ctok.type = "COLON"
                yield ctok
                implied_colon_needed = False
            yield token
        else:
            yield token


# only care about whitespace at the start of a line
def track_tokens_filter(lexer, tokens):
    oldignore = lexer.lexignore
    lexer.at_line_start = at_line_start = True
    indent = NO_INDENT
    saw_colon = False
    for token in tokens:
        #print ("track token", token, token.type)
        token.at_line_start = at_line_start

        if token.type == "COLON":
            at_line_start = False
            indent = MAY_INDENT
            token.must_indent = False

        elif token.type == "NEWLINE":
            at_line_start = True
            if indent == MAY_INDENT:
                indent = MUST_INDENT
            token.must_indent = False

        elif token.type == "WS":
            assert token.at_line_start == True
            at_line_start = True
            token.must_indent = False

        else:
            # A real token; only indent after COLON NEWLINE
            if indent == MUST_INDENT:
                token.must_indent = True
            else:
                token.must_indent = False
            at_line_start = False
            indent = NO_INDENT

        # really bad hack that changes ignore lexer state.
        # when "must indent" is seen (basically "real tokens" seen)
        # then ignore whitespace.
        if token.must_indent:
            lexer.lexignore = ('ignore', ' ')
        else:
            lexer.lexignore = oldignore

        token.indent = indent
        yield token
        lexer.at_line_start = at_line_start


def _new_token(type, lineno):
    tok = lex.LexToken()
    tok.type = type
    tok.value = None
    tok.lineno = lineno
    tok.lexpos = -1
    return tok

# Synthesize a DEDENT tag


def DEDENT(lineno):
    return _new_token("DEDENT", lineno)

# Synthesize an INDENT tag


def INDENT(lineno):
    return _new_token("INDENT", lineno)


def count_spaces(l):
    for i in range(len(l)):
        if l[i] != ' ':
            return i
    return 0


def annoying_case_hack_filter(code):
    """add annoying "silent keyword" (fallthrough)

    this which tricks the parser into taking the (silent) case statement
    as a "small expression".  it can then be spotted and used to indicate
    "fall through" to the next case (in the parser)

    also skips blank lines

    bugs: any function that starts with the letters "case" or "default"
    will be detected erroneously.  fixing that involves doing a token
    lexer which spots the fact that "case" and "default" are words,
    separating them from space, colon, bracket etc.

    http://bugs.libre-riscv.org/show_bug.cgi?id=280
    """
    res = []
    prev_spc_count = None
    for l in code.split("\n"):
        spc_count = count_spaces(l)
        nwhite = l[spc_count:]
        if len(nwhite) == 0:  # skip blank lines
            res.append('')
            continue
        if nwhite.startswith("case") or nwhite.startswith("default"):
            #print ("case/default", nwhite, spc_count, prev_spc_count)
            if (prev_spc_count is not None and
                prev_spc_count == spc_count and
                    (res[-1].endswith(":") or res[-1].endswith(": fallthrough"))):
                res[-1] += " fallthrough"  # add to previous line
            prev_spc_count = spc_count
        else:
            #print ("notstarts", spc_count, nwhite)
            prev_spc_count = None
        res.append(l)
    return '\n'.join(res)


# Track the indentation level and emit the right INDENT / DEDENT events.
def indentation_filter(tokens, filename):
    # A stack of indentation levels; will never pop item 0
    levels = [0]
    token = None
    depth = 0
    prev_was_ws = False
    for token in tokens:
        if 0:
            print("Process", depth, token.indent, token,)
            if token.at_line_start:
                print("at_line_start",)
            if token.must_indent:
                print("must_indent",)
            print

        # WS only occurs at the start of the line
        # There may be WS followed by NEWLINE so
        # only track the depth here.  Don't indent/dedent
        # until there's something real.
        if token.type == "WS":
            assert depth == 0
            depth = len(token.value)
            prev_was_ws = True
            # WS tokens are never passed to the parser
            continue

        if token.type == "NEWLINE":
            depth = 0
            if prev_was_ws or token.at_line_start:
                # ignore blank lines
                continue
            # pass the other cases on through
            yield token
            continue

        # then it must be a real token (not WS, not NEWLINE)
        # which can affect the indentation level

        prev_was_ws = False
        if token.must_indent:
            # The current depth must be larger than the previous level
            if not (depth > levels[-1]):
                raise_syntax_error("expected an indented block",
                                   filename, token.lexer.lineno,
                                   token.lexer.lexpos, token.lexer.lexdata,
                                   cls=IndentationError)

            levels.append(depth)
            yield INDENT(token.lineno)

        elif token.at_line_start:
            # Must be on the same level or one of the previous levels
            if depth == levels[-1]:
                # At the same level
                pass
            elif depth > levels[-1]:
                raise_syntax_error("indent increase but not in new block",
                                   filename, token.lexer.lineno,
                                   token.lexer.lexpos, token.lexer.lexdata,
                                   cls=IndentationError)
            else:
                # Back up; but only if it matches a previous level
                try:
                    i = levels.index(depth)
                except ValueError:
                    raise_syntax_error("inconsistent indentation",
                                       filename, token.lexer.lineno,
                                       token.lexer.lexpos, token.lexer.lexdata,
                                       cls=IndentationError)
                for _ in range(i+1, len(levels)):
                    yield DEDENT(token.lineno)
                    levels.pop()

        yield token

    ### Finished processing ###

    # Must dedent any remaining levels
    if len(levels) > 1:
        assert token is not None
        for _ in range(1, len(levels)):
            yield DEDENT(token.lineno)


# The top-level filter adds an ENDMARKER, if requested.
# Python's grammar uses it.
def filter(lexer, add_endmarker, filename):
    token = None
    tokens = iter(lexer.token, None)
    tokens = python_colonify(lexer, tokens)
    tokens = track_tokens_filter(lexer, tokens)
    for token in indentation_filter(tokens, filename):
        yield token

    if add_endmarker:
        lineno = 1
        if token is not None:
            lineno = token.lineno
        yield _new_token("ENDMARKER", lineno)


KEYWORD_REPLACEMENTS = {'class': 'class_'}

##### Lexer ######


class PowerLexer:
    tokens = (
        'DEF',
        'IF',
        'THEN',
        'ELSE',
        'FOR',
        'TO',
        'DO',
        'WHILE',
        'BREAK',
        'NAME',
        'HEX',     # hex numbers
        'NUMBER',  # Python decimals
        'BINARY',  # Python binary
        'STRING',  # single quoted strings only; syntax of raw strings
        'LPAR',
        'RPAR',
        'LBRACK',
        'RBRACK',
        'COLON',
        'EQ',
        'ASSIGNEA',
        'ASSIGN',
        'LTU',
        'GTU',
        'NE',
        'LE',
        'LSHIFT',
        'RSHIFT',
        'GE',
        'LT',
        'GT',
        'PLUS',
        'MINUS',
        'MULT',
        'DIV',
        'MOD',
        'INVERT',
        'APPEND',
        'BITOR',
        'BITAND',
        'BITXOR',
        'RETURN',
        'SWITCH',
        'CASE',
        'DEFAULT',
        'WS',
        'NEWLINE',
        'COMMA',
        'QMARK',
        'PERIOD',
        'SEMICOLON',
        'INDENT',
        'DEDENT',
        'ENDMARKER',
    )

    # Build the lexer
    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)
        self.filename = None

    def t_HEX(self, t):
        r"""0x[0-9a-fA-F_]+"""
        val = t.value.replace("_", "")
        t.value = SelectableInt(int(val, 16), (len(val)-2)*4)  # hex = nibble
        return t

    def t_BINARY(self, t):
        r"""0b[01_]+"""
        val = t.value.replace("_", "")
        t.value = SelectableInt(int(val, 2), len(val)-2)
        return t

    #t_NUMBER = r'\d+'
    # taken from decmial.py but without the leading sign
    def t_NUMBER(self, t):
        r"""(\d+(\.\d*)?|\.\d+)([eE][-+]? \d+)?"""
        t.value = int(t.value)
        return t

    def t_STRING(self, t):
        r"'([^\\']+|\\'|\\\\)*'"  # I think this is right ...
        print(repr(t.value))
        t.value = t.value[1:-1]
        return t

    t_COLON = r':'
    t_EQ = r'='
    t_ASSIGNEA = r'<-iea'
    t_ASSIGN = r'<-'
    t_LTU = r'<u'
    t_GTU = r'>u'
    t_NE = r'!='
    t_LE = r'<='
    t_GE = r'>='
    t_LSHIFT = r'<<'
    t_RSHIFT = r'>>'
    t_LT = r'<'
    t_GT = r'>'
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_MULT = r'\*'
    t_DIV = r'/'
    t_MOD = r'%'
    t_INVERT = r'¬'
    t_COMMA = r','
    t_PERIOD = r'.'
    t_SEMICOLON = r';'
    t_APPEND = r'\|\|'
    t_BITOR = r'\|'
    t_BITAND = r'\&'
    t_BITXOR = r'\^'
    t_QMARK = r'\?'

    # Ply nicely documented how to do this.

    RESERVED = {
        "def": "DEF",
        "if": "IF",
        "then": "THEN",
        "else": "ELSE",
        "leave": "BREAK",
        "for": "FOR",
        "to": "TO",
        "while": "WHILE",
        "do": "DO",
        "return": "RETURN",
        "switch": "SWITCH",
        "case": "CASE",
        "default": "DEFAULT",
    }

    def t_NAME(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        t.type = self.RESERVED.get(t.value, "NAME")
        if t.value in KEYWORD_REPLACEMENTS:
            t.value = KEYWORD_REPLACEMENTS[t.value]
        return t

    # Putting this before t_WS let it consume lines with only comments in
    # them so the latter code never sees the WS part.  Not consuming the
    # newline.  Needed for "if 1: #comment"
    def t_comment(self, t):
        r"[ ]*\043[^\n]*"  # \043 is '#'
        pass

    # Whitespace

    def t_WS(self, t):
        r'[ ]+'
        if t.lexer.at_line_start and t.lexer.paren_count == 0 and \
                t.lexer.brack_count == 0:
            return t

    # Don't generate newline tokens when inside of parenthesis, eg
    #   a = (1,
    #        2, 3)
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        t.type = "NEWLINE"
        if t.lexer.paren_count == 0 and t.lexer.brack_count == 0:
            return t

    def t_LBRACK(self, t):
        r'\['
        t.lexer.brack_count += 1
        return t

    def t_RBRACK(self, t):
        r'\]'
        # check for underflow?  should be the job of the parser
        t.lexer.brack_count -= 1
        return t

    def t_LPAR(self, t):
        r'\('
        t.lexer.paren_count += 1
        return t

    def t_RPAR(self, t):
        r'\)'
        # check for underflow?  should be the job of the parser
        t.lexer.paren_count -= 1
        return t

    #t_ignore = " "

    def t_error(self, t):
        raise_syntax_error("Unknown symbol %r" % (t.value[0],),
                           self.filename, t.lexer.lineno,
                           t.lexer.lexpos, t.lexer.lexdata)
        print("Skipping", repr(t.value[0]))
        t.lexer.skip(1)


# Combine Ply and my filters into a new lexer

class IndentLexer(PowerLexer):
    def __init__(self, debug=0, optimize=0, lextab='lextab', reflags=0):
        self.debug = debug
        self.build(debug=debug, optimize=optimize,
                   lextab=lextab, reflags=reflags)
        self.token_stream = None

    def input(self, s, add_endmarker=True):
        s = annoying_case_hack_filter(s)
        if self.debug:
            print(s)
        s += "\n"
        self.lexer.paren_count = 0
        self.lexer.brack_count = 0
        self.lexer.lineno = 1
        self.lexer.input(s)
        self.token_stream = filter(self.lexer, add_endmarker, self.filename)

    def token(self):
        try:
            return next(self.token_stream)
        except StopIteration:
            return None


switchtest = """
switch (n)
    case(1): x <- 5
    case(3): x <- 2
    case(2):

    case(4):
        x <- 3
    case(9):

    default:
        x <- 9
print (5)
"""

cnttzd = """
n  <- 0
do while n < 64
   if (RS)[63-n] = 0b1 then
        leave
   n  <- n + 1
RA <- EXTZ64(n)
print (RA)
"""

if __name__ == '__main__':

    # quick test/demo
    #code = cnttzd
    code = switchtest
    print(code)

    lexer = IndentLexer(debug=1)
    # Give the lexer some input
    print("code")
    print(code)
    lexer.input(code)

    tokens = iter(lexer.token, None)
    for token in tokens:
        print(token)

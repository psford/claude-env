#!/usr/bin/env python3
"""Find the exceptions a guard grants, by shape rather than by spelling.

CE-12.4. hatch_authoring_guard's first scan looked for a token SPELLING --
`NAME-OK` followed by a colon -- because that is what the 26 known
command-text hatches looked like. It therefore could not see:

    ESCAPE = "CWD_DRIFT_OK"        underscores, no colon
    if ESCAPE in command:          the exact mechanism the epic is named
        return 0                   after

and it did not see `--ignore-engines` either, a plain flag that waives
engines_node_guard outright. Widening the spelling was tried twice and was
worse: matching identifiers flagged 261 ordinary constants, and matching
string literals flagged 66. Both would have blocked every commit.

SO ASK THE STRUCTURAL QUESTION INSTEAD. A guard that waives itself on
something in the command text has one shape:

    if <literal> in <command>:     ->  return / return 0

and a guard that merely establishes whether it APPLIES has the negation of
it:

    if <literal> not in <command>: ->  return / return 0

Measured across all 51 hooks: nine of the second, one of the first. The
negation is the whole discriminator, it needs no list, and a token nobody
has ever written is found the first time it appears.

This module is the scanner. hatch_authoring_guard is what refuses.
"""

import ast

# The names a hook gives the text it was handed. Not a guess: these are the
# only ones the 51 hooks in this directory actually use.
COMMAND_NAMES = frozenset({"command", "cmd", "text", "message", "body"})


def _literal_of(node, consts):
    """The string this node evaluates to, if it plainly evaluates to one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    return None


def _module_constants(tree):
    """Module-level NAME = "literal" bindings, so `ESCAPE` resolves."""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = node.value.value
    return out


def _stops_checking(body):
    """True when this branch abandons the check rather than doing something."""
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    value = body[0].value
    return value is None or (isinstance(value, ast.Constant)
                             and value.value in (0, None))


def waivers(source):
    """[(line, token)] for every exception this source grants on command text.

    An `in` that abandons the check is a waiver. A `not in` that abandons it
    is a trigger -- the guard deciding it does not apply -- and is left
    alone. That asymmetry is the entire test.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    consts = _module_constants(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        if not isinstance(test.ops[0], ast.In):
            continue
        comparator = test.comparators[0]
        if not (isinstance(comparator, ast.Name)
                and comparator.id in COMMAND_NAMES):
            continue
        if not _stops_checking(node.body):
            continue
        token = _literal_of(test.left, consts)
        found.append((node.lineno, token if token is not None
                      else ast.unparse(test.left)))
    return found

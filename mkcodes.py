import os
import re
import glob
import warnings
import argparse

try:
    import markdown as markdown_enabled
except ImportError:
    markdown_enabled = False
else:
    from markdown.extensions import Extension
    from markdown.treeprocessors import Treeprocessor


def github_codeblocks(filepath, safe):
    codeblocks = []
    codeblock_re = r'^```.*'
    codeblock_open_re = r'^```(`*)(py|python){0}$'.format('' if safe else '?')

    with open(filepath, 'r', encoding="utf-8") as f:
        block = []
        python = True
        in_codeblock = False

        for line in f.readlines():
            codeblock_delimiter = re.match(codeblock_re, line)

            if in_codeblock:
                if codeblock_delimiter:
                    if python:
                        codeblocks.append(''.join(block))
                    block = []
                    python = True
                    in_codeblock = False
                else:
                    block.append(line)
            elif codeblock_delimiter:
                in_codeblock = True
                if not re.match(codeblock_open_re, line):
                    python = False
    return codeblocks


def markdown_codeblocks(filepath, safe):
    import markdown

    codeblocks = []

    if safe:
        warnings.warn("'safe' option not available in 'markdown' mode.")

    class DoctestCollector(Treeprocessor):
        def run(self, root):
            nonlocal codeblocks
            codeblocks = (block.text for block in root.iterfind('./pre/code'))

    class DoctestExtension(Extension):
        def extendMarkdown(self, md, md_globals):
            md.registerExtension(self)
            md.treeprocessors.add("doctest", DoctestCollector(md), '_end')

    doctestextension = DoctestExtension()
    markdowner = markdown.Markdown(extensions=[doctestextension])
    markdowner.convertFile(filepath, output=os.devnull)
    return codeblocks


def is_markdown(f):
    markdown_extensions = ['.markdown', '.mdown', '.mkdn', '.mkd', '.md']
    return os.path.splitext(f)[1] in markdown_extensions


def get_nested_files(directory, depth):
    for i in glob.iglob(directory + '/*'):
        if os.path.isdir(i):
            yield from get_nested_files(i, depth+1)
        elif is_markdown(i):
            yield (i, depth)


def get_files(inputs):
    for i in inputs:
        if os.path.isdir(i):
            yield from get_nested_files(i, 0)
        elif is_markdown(i):
            yield (i, 0)


def makedirs(directory):
    to_make = []

    while directory:
        try:
            os.mkdir(directory)
        except FileNotFoundError:
            directory, tail = os.path.split(directory)
            to_make.append(tail)
        else:
            with open(os.path.join(directory, '__init__.py'), 'w', encoding="utf-8"):
                pass
            if to_make:
                directory = os.path.join(directory, to_make.pop())
            else:
                break


argParser = argparse.ArgumentParser()
argParser.add_argument("--output", default=os.path.join("output", '{name}.py'), help="output dir")
argParser.add_argument("--github", default=(bool(markdown_enabled)), help="Ture/False")
argParser.add_argument("--safe", default=True, help="Extract codeblock with language hints only")
argParser.add_argument("input", help="Input directory")

args = argParser.parse_args()

def main(inputs, output, github, safe):
    collect_codeblocks = github_codeblocks if github else markdown_codeblocks
    output = output.replace("{name}", "{name}_{index}")

    for filepath, depth in get_files(inputs):
        codeblocks = collect_codeblocks(filepath, safe)

        if codeblocks:
            outputname = os.sep.join(filepath.split(os.sep)[-1-depth:])

            for i, blockitem in enumerate(codeblocks):
                
                outputfilename = output.format(name=outputname, index=i)

                outputdir = os.path.dirname(outputfilename)
                if not os.path.exists(outputdir):
                    makedirs(outputdir)

                with open(outputfilename, 'w', encoding="utf-8") as outputfile:
                    outputfile.write(blockitem)

if __name__ == "__main__":
    main([args.input], args.output, args.github, args.safe)
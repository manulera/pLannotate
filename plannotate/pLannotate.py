import argparse
import os

import click
import streamlit.cli
from bokeh.embed import file_html
from bokeh.resources import CDN

import plannotate.resources as rsc
from plannotate.annotate import annotate
from plannotate.BLAST_hit_details import details
from plannotate.bokeh_plot import get_bokeh
from plannotate.streamlit_app import run_streamlit
from plannotate import __file__ as plannotate_file

#possible file structure for better containment
# plasmid = {
#     'fileloc': '',
#     'name': '',
#     'ext': '',
#     'blast_db': './BLAST_dbs/',
#     'linear': False,
#     'seq': '',
#     'raw_hits': pd.DataFrame(),
#     'hits': pd.DataFrame(),
#     'hits_detailed' : pd.DataFrame()
# }

# NOTE: streamline really wants us to use their entry point and give
#       them a script to run. Here we follow the hello world example
#       to bootstrap running of this file as a script (the streamlit_run
#       function). Unfortunately we have to buy in to using click as
#       the command-line parse in front of streamlit, but then also
#       use standard argparse to parse the final options in our script.


@click.group()
@click.version_option(prog_name=__package__)
def main():
    pass


@main.command("streamlit")
@streamlit.cli.configurator_options
@click.option('--blast_db', default=os.path.join(os.path.dirname(plannotate_file),"BLAST_dbs"), help="path to BLAST databases.")
def main_streamlit(blast_db, **kwargs):
    # taken from streamlit.cli.main_hello, @0.78.0
    streamlit.cli._apply_config_options_from_cli(kwargs)
    # TODO: do this better?
    args = ['--blast_db', blast_db]
    streamlit.cli._main_run(__file__, args)


@main.command("batch")
@click.option("--input","-i", 
                help=f"location of a FASTA or GBK file; < {rsc.maxPlasSize:,} bases")
@click.option("--output","-o", default = f"./",  
                help="location of output folder. DEFAULT: current dir")
@click.option("--file_name","-f", default = "",  
                help="name of output file (do not add extension). DEFAULT: proceedurally generated name")
@click.option("--suffix","-s", default = "_pLann",  
                help="suffix appended to output files. Use '' for no suffix. DEFAULT: '_pLann'")
@click.option("--blast_db","-b", default=os.path.join(os.path.dirname(plannotate_file),"BLAST_dbs"), 
                help="path to BLAST databases. DEFAULT: builtin")
@click.option("--linear","-l", is_flag=True, 
                help="enables linear DNA annotation")
@click.option("--html","-h", is_flag=True, 
                help="creates an html plasmid map in specified path")
@click.option("--csv","-c", is_flag=True, 
                help="creates a cvs file in specified path")
@click.option("--detailed","-d", is_flag=True, 
                help="uses modified algorithm for a more-detailed search with more false positives")
@click.option("--no_gbk","-x", is_flag=True, 
                help="supresses GenBank output file")
def main_batch(blast_db,input,output,file_name,suffix,linear,html,csv,detailed,no_gbk):
    """
    Annotates engineered DNA sequences, primarily plasmids. Accepts a FASTA or GenBank file and outputs
    a GenBank file with annotations, as well as an optional interactive plasmid map as an HTLM file.
    """

    name, ext = rsc.get_name_ext(input)

    if file_name == "":
        file_name = name

    inSeq = rsc.validate_file(input, ext)

    recordDf = annotate(inSeq, blast_db, linear, detailed)
    recordDf = details(recordDf, blast_db)

    if no_gbk == False:
        gbk = rsc.get_gbk(recordDf, inSeq, linear)
        with open(f"{output}/{file_name}{suffix}.gbk", "w") as handle:
            handle.write(gbk)

    if html:
        bokeh_chart = get_bokeh(recordDf, linear)
        bokeh_chart.sizing_mode = "fixed"
        html = file_html(bokeh_chart, resources = CDN, title = f"{output}.html")
        with open(f"{output}/{file_name}{suffix}.html", "w") as handle:
            handle.write(html)

    if csv:
        csv_df = rsc.get_clean_csv_df(recordDf)
        csv_df.to_csv(f"{output}/{file_name}{suffix}.csv", index = None)


def streamlit_run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blast_db")
    args =  parser.parse_args()

    run_streamlit(args)

if __name__ == '__main__':
    streamlit_run()

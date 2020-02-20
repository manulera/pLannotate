import streamlit as st
import numpy as np
import base64
from Bio import SeqIO
from tempfile import NamedTemporaryFile
import pandas as pd
from annotate3 import annotate, get_gbk
from visualizations import plot_plas #deprecated?
from bokeh_plot import get_bokeh


# from bokeh_ex import get_bokeh
# st.bokeh_chart(get_bokeh(),use_container_width=False)


st.image("./images/pLannotate.png",use_column_width=True, width=500)
st.subheader('v0.2')

st.sidebar.markdown('''
        **<a href="https://en.wikipedia.org/wiki/Plasmid" target="_blank">Plasmids</a>** are ubiquitous in many fields of biology.

        Engineered plasmids generally have long and circuitous cloning histories, meaning annotations are forgotten, and often contain hidden junk leftover from cloning.

        **<font color="#f9a557">pLannotate</font>** re-annotates engineered plasmids and shows you where the junk is.''',unsafe_allow_html=True)

inSeq=""

option = st.radio(
    'Choose method of submitting sequence:',
    ["Upload a file (.fa or .fasta)", "Enter a sequence","Example"])

if option == "Upload a file (.fa or .fasta)":
    uploaded_file = st.file_uploader("Choose a file:", type=['fa',"fasta"])
    if uploaded_file is not None:
        st.success("File uploaded.")
        file=uploaded_file.readlines()
        inSeq="".join(file[1:]).strip().replace("\n","").replace("\r","")
elif option == "Enter a sequence":
    inSeq = st.text_area('Input sequence here:')
elif option == "Example":
    exampleFile=st.radio("Choose example file:",("pSC101","pPAGFP-C","pCA-mTmG"))
    inSeq=str(list(SeqIO.parse(f"./fastas/{exampleFile}.fa", "fasta"))[0].seq)
    st.text_area('Input sequence here:',inSeq)

if inSeq:

    st.write(len(inSeq))

    with st.spinner("Annotating..."):
        recordDf = annotate(inSeq)

        if recordDf.empty:
            st.error("No annotations found.")
        else:

            st.markdown("---")
            st.header('Results:')

            #can remove inSeq len -- encoded in DF (slen?)
            st.bokeh_chart(get_bokeh(recordDf),use_container_width=False)

            #for dna_feature_viewer
            # ax = plot_plas(record)
            # st.pyplot(bbox_inches="tight",transparent = True,pad_inches=0.1)

            featureDescriptions=pd.read_csv("./feature_notes.csv",sep="\t",index_col=0)
            st.markdown(featureDescriptions.loc[recordDf.index].set_index("Feature",drop=True).drop_duplicates().to_markdown())

            st.markdown("---")
            st.header("Download Annotations:")

            filename = st.text_input('Enter custom file name for download:',"pLannotate")
            if not filename:
                filename="pLannotate"

            #write and encode gbk for dl
            gbk=get_gbk(recordDf,inSeq)
            b64 = base64.b64encode(gbk.encode()).decode()
            dlPicLoc='https://raw.githubusercontent.com/barricklab/pLannotate/master/images/dl_arrow.png?token=AEGCMHBG4PXBX5UDRMJRCGC6KL3NM'
            gbk_dl = f'<a href="data:text/plain;base64,{b64}" download="{filename}.gbk"> ![dl]({dlPicLoc} "download .gbk") download {filename}.gbk</a>'
            st.markdown(gbk_dl, unsafe_allow_html=True)

            #encode csv for dl
            csv = recordDf.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            csv_dl = f'<a href="data:text/plain;base64,{b64}" download="{filename}.csv"> ![dl]({dlPicLoc} "download .csv") download {filename}.csv</a>'
            st.markdown(csv_dl, unsafe_allow_html=True)

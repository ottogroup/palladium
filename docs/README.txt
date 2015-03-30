Palladium's documentation is based on Sphinx. In order to build the
documentation, it is required that Sphinx is installed (e.g., by using
'pip install Sphinx'). In order to generate an HTML version of the
documentation, run the following command in the docs folder:

make html

Documentation will then be available at
<palladium_checkout_folder>/docs/_build/html/index.html.

If you want to create a PDF version of Palladium's documentation, you
have to make sure that pdflatex is installed. On Ubuntu you need to
install the following packages:

sudo apt-get install texlive-latex-base
sudo apt-get install texlive-latex-extra
sudo apt-get install texlive-fonts-recommended

If pdflatex and needed fonts are installed, you can create the
documentation running the following command:

make latexpdf

Documentation will then be available at
<palladium_checkout_folder>/docs/_build/latex/Palladium.pdf.

Troubleshooting
---------------

It has been reported that in some settings (Mac), Sphinx might stop
with the error "ValueError: unknown locale: UTF-8". In this case, the
environment has to be changed, e.g., as follows before generating the
documentation (see
http://stackoverflow.com/questions/10921430/fresh-installation-of-sphinx-quickstart-fails):

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

all: wiki concept

wiki:
	@mkdir wiki ; \
	./man2wiki ; \
	mv *-wiki wiki

concept:
	@mkdir concept ; \
	latex --output-directory=concept articlefak-concept.tex ; \
	dvipdf concept/articlefak-concept.dvi concept/articlefak-concept.pdf

clean:
	rm -rf wiki
	rm -rf concept

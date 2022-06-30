from flask import Flask
from flask_restful import Api
from rpy2.rinterface_lib.sexp import NACharacterType
import rpy2.robjects.packages as packages
from rpy2.robjects.vectors import DataFrame as rdf
import pandas as pd
import numpy as np
import json
from datetime import datetime
import os

from flask import Flask, request
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from


app = Flask(__name__)
api = Api(app)


class MyEncoder(json.JSONEncoder):
    """
    custom JSON encoder. Converts certain datatypes to valid JSON.
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, NACharacterType):
            obj = None
            return obj
        elif isinstance(obj, pd.DataFrame):
            pass
        elif isinstance(obj, rdf):
            df_obj = pd.DataFrame.from_dict({key: np.asarray(obj.rx2(key)) for key in obj.names}, orient='index')
            df_obj = df_obj.T
            df_obj = df_obj.to_dict()
            return df_obj
        else:
            return super(MyEncoder, self).default(obj)


class RPackageDependencies:
    """
    This class handles the install and/or import of the most up-to-date
    R package we use with this API.
    """

    def __init__(self, r_package):
        self.r_package = r_package
        utils = packages.importr('utils')
        utils.chooseCRANmirror(ind=1)
        self.source_package = None
        self.package_import = self.import_source_package(self.r_package)

    def import_source_package(self, package_name):
        """
        Install and/or import the most up-to-date source package.
        """
        if packages.isinstalled(package_name):
            self.source_package = packages.importr(package_name)
            if self.check_latest_release_version(package_name):
                return self.source_package
            else:
                self.install_package(package_name)

    def install_package(self, package_name):
        """
        Installs the source package using the R utils package.
        """
        utils = packages.importr('utils')
        utils.chooseCRANmirror(ind=1)
        utils.install_packages(package_name)
        self.source_package = packages.importr(package_name)
        return self.source_package

    def check_latest_release_version(self, package):
        """
        check if imported source package is latest available version.
        """
        utils = packages.importr('utils')
        installed_package = self.extract_version(utils.installed_packages())
        available_package = self.extract_version(utils.available_packages())
        is_latest_version = installed_package[package] == available_package[package]
        return is_latest_version

    def extract_version(self, package_data):
        """
        Get package and version column.
        """
        return dict(zip(package_data.rx(True, 'Package'), package_data.rx(True, 'Version')))


class InvalidSource(Exception):
    """
    Validation for input source.
    """
    def __init__(self, input_source, valid_sources):
        self.input_source = input_source
        self.invalid_source_message = f"""
            '{self.input_source}' is an invalid data source. Please select one of the following:
            {valid_sources}.
        """
        super().__init__(self.invalid_source_message)


class NoCompetitionData(Exception):
    """
    Validation for competition.
    """
    def __init__(self, input_competition, valid_competitions):
        self.input_competition = input_competition
        self.invalid_source_message = f"""
            '{self.input_competition}' is an invalid data source. Please select one of the following:
            {valid_competitions}.
        """
        super().__init__(self.invalid_source_message)


class InvalidRoundNumber(Exception):
    """
    Validation for round_number.
    """
    def __init__(self, input_round_number):
        self.input_round_number = input_round_number
        self.invalid_source_message = f"""
            '{self.input_round_number}' is an invalid round_number. Please enter a valid number."""
        super().__init__(self.invalid_source_message)


class InvalidSeason(Exception):
    """
    Validation for season.
    """
    def __init__(self, input_season):
        self.input_season = input_season
        self.invalid_source_message = f"""
            '{self.input_season}' is an invalid season. Please enter a valid number."""
        super().__init__(self.invalid_source_message)


@app.route('/', methods=['GET'])
def home():
    #TODO Use Python to load swagger doc to the home page!
    return 'Hello there!'



@app.route('/playerstats/<int:season>,<int:round_number>,<string:source>', methods=['GET'])
def player_stats(**kwargs):

    r_package = packages.importr('fitzRoy')

    season = kwargs.get('season', datetime.now().year)
    round_number = kwargs.get('round_number', '')
    source = kwargs.get('source', 'AFL')

    # season input validation
    if not isinstance(season, int):
        try:
            season = int(season)
        except:
            raise InvalidSeason(season)

    # source input validation
    valid_sources = ('AFL', 'footywire', 'fryzigg', 'afltables')
    if source not in valid_sources:
        raise InvalidSource(source, valid_sources)

    if source.upper() not in ('AFL', 'AFLM') and round_number:
        print('''round_number is currently only supported with the 'AFL' source.
                 Returning data for all rounds in specified season.''')

    response = r_package.fetch_player_stats(season=season, source=source, round_number=round_number)

    player_stats = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    player_stats = player_stats.T

    player_stats = player_stats.to_dict()

    player_stats = json.dumps(player_stats, cls=MyEncoder)

    return player_stats


@app.route('/fixture/<int:season>,<int:round_number>,<string:competition>', methods=['GET'])
def fixture(**kwargs):

    r_package = packages.importr('fitzRoy')

    season = kwargs.get('season', datetime.now().year)
    round_number = kwargs.get('round_number', '')
    source = kwargs.get('source', 'AFL')
    competition = kwargs.get('competition', 'AFLM')

    # round_number input validation
    if source != 'AFL' and round_number == '':
        # TODO Improvement: If round_number is an empty string return all rounds
        round_number = 1

    # competition input validation
    valid_competitions = ('AFLM', 'AFLW',)
    if source != 'AFL':
        valid_competitions = ('AFLM',)
    if competition.upper() not in valid_competitions:
        raise NoCompetitionData(competition, valid_competitions)

    response = r_package.fetch_fixture(season=season, round_number=round_number, source=source, comp=competition)

    fixture = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key), dtype=object) for key in response.names}, orient='index')

    fixture = fixture.T

    fixture = fixture.to_dict()

    fixture = json.dumps(fixture, cls=MyEncoder)

    return fixture


@app.route('/lineup/<int:season>,<int:round_number>,<string:competition>', methods=['GET'])
def lineup(**kwargs):

    r_package = packages.importr('fitzRoy')

    season = kwargs.get('season', datetime.now().year)
    round_number = kwargs.get('round_number', 1)
    competition = kwargs.get('competition', 'AFLM')

    response = r_package.fetch_lineup(season=season, round_number=round_number, comp=competition)

    lineup = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    lineup = lineup.T

    lineup = lineup.to_dict()

    lineup = json.dumps(lineup, cls=MyEncoder)

    return lineup


@app.route('/results/<int:season>,<int:round_number>,<string:competition>', methods=['GET'])
def results(**kwargs):

    r_package = RPackageDependencies('fitzRoy')

    round_number = kwargs.get('round_number', 1)
    season = kwargs.get('season', datetime.now().year if round_number else datetime.now().year - 1)
    source = kwargs.get('source', 'AFL')
    competition = kwargs.get('competition', 'AFLM')

    if not isinstance(season, int):
        try:
            season = int(season)
        except:
            raise InvalidSeason(season)

    if not isinstance(round_number, int):
        try:
            round_number = int(round_number)
        except:
            raise InvalidRoundNumber(round_number)

    # source input validation
    valid_sources = ('footywire', 'fryzigg', 'afltables', 'AFL')
    if source not in valid_sources:
        raise InvalidSource(source, valid_sources)

    response = r_package.source_package.fetch_results(season=season, round_number=round_number, comp=competition)

    results = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    results = results.T

    results = results.to_dict()

    results = json.dumps(results, cls=MyEncoder)

    return results


@app.route('/ladder/<int:season>,<string:source>', methods=['GET'])
def ladder(**kwargs):

    r_package = packages.importr('fitzRoy')

    season = kwargs.get('season', datetime.now().year)
    round_number = kwargs.get('round_number', 1)
    source = kwargs.get('source', 'AFL')
    competition = kwargs.get('competition', 'AFLM')

    # competition input validation
    valid_competitions = ('AFLM', 'AFLW')
    if source not in ('AFL', 'fryzigg',):
        valid_competitions = ('AFLM',)
    if competition.upper() not in valid_competitions:
        raise NoCompetitionData(competition, valid_competitions)

    # season input validation
    if not isinstance(season, int):
        try:
            season = int(season)
        except:
            raise InvalidSeason(season)

    # round_number input validation
    if not isinstance(round_number, int):
        try:
            round_number = int(round_number)
        except:
            raise InvalidRoundNumber(round_number)

    # source input validation
    valid_sources = ('AFL', 'squiggle', 'afltables')
    if source not in valid_sources:
        raise InvalidSource(source, valid_sources)

    response = r_package.fetch_ladder(season=season, source=source, round_number=round_number, comp=competition)

    ladder = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    ladder = ladder.T

    ladder = ladder.to_dict()

    ladder = json.dumps(ladder, cls=MyEncoder)

    return ladder


@app.route('/player_details/<string:team>,<string:current>,<string:source>', methods=['GET'])
def player_details(**kwargs):

    r_package = packages.importr('fitzRoy')

    source = kwargs.get('source', 'AFL')
    current = kwargs.get('current', True)
    team = kwargs.get('team', '')

    response = r_package.fetch_player_details(team=team, current=current, source=source)

    player_details = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    player_details = player_details.T

    player_details = player_details.to_dict()

    player_details = json.dumps(player_details, cls=MyEncoder)

    return player_details


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port)

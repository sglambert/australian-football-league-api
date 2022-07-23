
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import rpy2.robjects.packages as packages
from flask import Flask, render_template, request
from flask_restful import Api
from rpy2.rinterface_lib.sexp import NACharacterType
from rpy2.robjects.vectors import DataFrame as rdf

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


@app.route('/')
def get_root():
    print('sending root')
    return render_template('index.html')


@app.route('/api/docs')
def get_api_docs():
    print('sending docs')
    return render_template('swaggerui.html')


@app.route('/fixture', methods=['GET'])
def fixture():

    r_package = packages.importr('fitzRoy')

    season = request.args.get('season', default=datetime.now().year, type=int)
    round_number = request.args.get('round_number', default=1)
    source = request.args.get('source', default='AFL', type=str)
    competition = request.args.get('competition', default='AFLM', type=str)

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


@app.route('/ladder', methods=['GET'])
def ladder():

    r_package = packages.importr('fitzRoy')

    season = request.args.get('season', default=datetime.now().year, type=int)
    round_number = request.args.get('round_number', default=1, type=int)
    source = request.args.get('source', default='AFL', type=str)
    competition = request.args.get('competition', default='AFLM', type=str)

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


@app.route('/lineup', methods=['GET'])
def lineup():

    r_package = packages.importr('fitzRoy')

    season = request.args.get('season', default=datetime.now().year, type=int)
    round_number = request.args.get('round_number', default=1, type=int)
    competition = request.args.get('competition', default='AFLM', type=str)

    response = r_package.fetch_lineup(season=season, round_number=round_number, comp=competition)

    lineup = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    lineup = lineup.T

    lineup = lineup.to_dict()

    lineup = json.dumps(lineup, cls=MyEncoder)

    return lineup


@app.route('/player_details', methods=['GET'])
def player_details():

    r_package = packages.importr('fitzRoy')

    source = request.args.get('source', default='AFL', type=str)
    current = request.args.get('current', default=True, type=bool)
    team = request.args.get('team', default='', type=str)

    response = r_package.fetch_player_details(team=team, current=current, source=source)

    player_details = pd.DataFrame.from_dict({key: np.asarray(response.rx2(key)) for key in response.names}, orient='index')

    player_details = player_details.T

    player_details = player_details.to_dict()

    player_details = json.dumps(player_details, cls=MyEncoder)

    return player_details


@app.route('/player_statistics', methods=['GET'])
def player_stats():

    r_package = packages.importr('fitzRoy')

    season = request.args.get('season', default=datetime.now().year, type=int)
    round_number = request.args.get('round_number', default='')
    source = request.args.get('source', default='AFL', type=str)

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


@app.route('/results', methods=['GET'])
def results():

    r_package = RPackageDependencies('fitzRoy')

    round_number = request.args.get('round_number', default=1, type=int)
    season = request.args.get('season', default=datetime.now().year, type=int)
    source = request.args.get('source', default='AFL', type=str)
    competition = request.args.get('competition', default='AFLM', type=str)

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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port)

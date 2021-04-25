#############################################################################
#
# Version 0.0.555 - Author: Asaf Ravid <asaf.rvd@gmail.com>
#
#    Stock Screener and Scanner - based on yfinance and investpy
#    Copyright (C) 2021 Asaf Ravid
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#############################################################################

from glob import glob
import csv
import yfinance as yf
import datetime
import numpy
import math
import pandas as pd
import sss

END_DATE_STR = '20210422'
RESULTS_LEN        = 28
TASE_MODE          = 0
RESULTS_INPUT_FOLDER = "Results/Nsr"
RESULTS_INPUT_PATH = "Results/Nsr/20201115-043117_FAVOUR_TECH_BY3_MARKETCAP_FORWARDEPS_PMARGIN0.17_EVR17.5_BUILD_DB_ONLY_NUM_RESULTS_1115"

results_input_paths = glob(RESULTS_INPUT_FOLDER+'/*/')


# Read Results Input:
def read_engine_results(path, max_results, sss_value_name):
    engine_results_list = []
    effective_row_index = 0
    sss_value_index     = -1

    try:
        with open(path, mode='r', newline='') as engine:
            reader = csv.reader(engine, delimiter=',')
            found_title_row = False
            for row in reader:
                if not found_title_row:
                    if row[0] == 'Ticker' or row[0] == 'Symbol':
                        found_title_row = True
                        sss_value_index = row.index(sss_value_name)
                    continue
                else:
                    if sss_value_index >= 0 and float(row[sss_value_index]) > 0.0:
                        engine_results_list.append(row[0])
                        effective_row_index += 1
                        if effective_row_index >= max_results:
                            break
    except Exception as e:
        # print('Exception {} in [read_engine_results]: path {}, max_results {}, sss_value_name {}'.format(e, path, max_results, sss_value_name))
        pass
    return engine_results_list


def find_start_date_value(symbol_to_check, start_date, pd_database_close_data):
    found_date = False
    current_date = start_date
    while not found_date:
        current_date_str = current_date.strftime('%Y-%m-%d')

        try:
            start_date_value_check = pd_database_close_data[symbol_to_check].loc[current_date_str]
        except Exception as e:
            current_date = current_date - datetime.timedelta(days=1)
            continue
        found_date = True

    return start_date_value_check


symbol_close_values_db = {}
sss_values_list        = ['sss', 'ssss', 'sssss']
pd_database_close      = None

for results_input_path in results_input_paths:
    results_input_path = results_input_path.replace("\\",'/')[:-1]
    print('\n Analyzing {}:'.format(results_input_path))
    results_date       = results_input_path.replace("Results","").replace("Nsr","").replace("All","").replace("Tase","").replace("/","")[:8]
    #                             year                    month                   day
    start = datetime.datetime(int(results_date[0:4]), int(results_date[4:6]), int(results_date[6:8]))
    end   = datetime.datetime(int(END_DATE_STR[0:4]), int(END_DATE_STR[4:6]), int(END_DATE_STR[6:8]))

    start = start - datetime.timedelta(days=1)

    results_lists               = []
    gains_lists                 = []
    performance_list            = []
    performance_indices_list    = []
    existence_in_db_ratios_list = []

    # Comparison Indices:
    if pd_database_close is None:
        comparison_indices_list     = ['SPY', 'QQQ', 'VTWO']
        data_start_end_indices_list = yf.download(comparison_indices_list, start=start, end=end, threads=False)
        data_start_end_indices_list = data_start_end_indices_list.Close
        pd_database_close = data_start_end_indices_list

    for sss_value_name in sss_values_list:
        results_list = read_engine_results(results_input_path+'/'+sss_value_name+'_engine.csv', RESULTS_LEN, sss_value_name+'_value')
        results_lists.append(results_list)

        existing_symbols_list = []
        new_symbols_list      = []
        gains_list            = []
        performance           = None
        existence_in_db_ratio = None
        if len(results_list):
            # Assuming folders are traversed alpphabetically, they will be scanned from oldest to newest, so dates may already exist:
            for symbol in results_list:
                if symbol in symbol_close_values_db:
                    existing_symbols_list.append(symbol)
                else:
                    new_symbols_list.append(symbol)

            if len(new_symbols_list):
                length_was_1 = False
                if len(new_symbols_list) == 1:  # take 1 from the existing, to get a proper-clumned dataframe
                    new_symbols_list.append(existing_symbols_list[0])
                    length_was_1 = True

                data_start_end_new_symbols_list = yf.download(new_symbols_list, start=start, end=end, threads=False)
                data_start_end_new_symbols_list = data_start_end_new_symbols_list.Close

                if length_was_1:
                    del data_start_end_new_symbols_list[existing_symbols_list[0]]

                if pd_database_close is None:
                    pd_database_close = data_start_end_new_symbols_list
                else:
                    pd_database_close = pd.concat([pd_database_close, data_start_end_new_symbols_list], axis=1, join="outer")

            for symbol in results_list:
                if symbol not in symbol_close_values_db:
                    symbol_close_values_db[symbol] = pd_database_close[symbol]

                start_date_value = find_start_date_value(symbol, start, pd_database_close)
                end_date_value   = pd_database_close[symbol][-1]
                if not math.isnan(start_date_value) and not math.isnan(end_date_value):
                    gains_list.append(round(end_date_value/start_date_value-1.0, sss.NUM_ROUND_DECIMALS))

            if not len(performance_indices_list):
                for comparison_indice in comparison_indices_list:
                    start_date_value = find_start_date_value(comparison_indice, start, pd_database_close)
                    end_date_value   = pd_database_close[comparison_indice][-1]
                    if not math.isnan(start_date_value) and not math.isnan(end_date_value):
                        performance_indices_list.append(round(100.0*(end_date_value / start_date_value - 1.0), sss.NUM_ROUND_DECIMALS))

            performance           = round(100*numpy.mean(gains_list), sss.NUM_ROUND_DECIMALS)
            existence_in_db_ratio = round(float(len(existing_symbols_list))/float(len(results_list)),sss.NUM_ROUND_DECIMALS)
        gains_lists.append(gains_list)
        performance_list.append(performance)
        existence_in_db_ratios_list.append(existence_in_db_ratio)

    print('     Performance % between {} and {} of {} is {}. DB existence ({}). {} Indices Performance Comparison: {}'.format(start,end, sss_values_list, performance_list, existence_in_db_ratios_list, comparison_indices_list, performance_indices_list))
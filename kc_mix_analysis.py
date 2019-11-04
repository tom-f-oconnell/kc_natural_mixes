#!/usr/bin/env python3

import os
from os.path import exists, join
import glob
from pprint import pprint as pp
import warnings
import time
import pickle

import numpy as np
#from scipy.optimize import minimize
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import seaborn as sns

import chemutils as cu

import hong2p.util as u


responder_threshold_plots = False
trial_matrices = False
odor_matrices = False
fit_matrices = False
#odor_and_fit_matrices = True
odor_and_fit_matrices = False
# TODO maybe modify things s.t. avg traces already go under
# odor_and_fit_matrices and odor_matrices (w/ gridspec probably)
# + eag too
avg_traces = True

test = False
#test = True

fig_dir = 'mix_figs'
if not exists(fig_dir):
    os.mkdir(fig_dir)

png_dir = join(fig_dir, 'png')
if not exists(png_dir):
    os.mkdir(png_dir)

'''
svg_dir = join(fig_dir, 'svg')
if not exists(svg_dir):
    os.mkdir(svg_dir)
'''

pdf_dir = join(fig_dir, 'pdf')
if not exists(pdf_dir):
    os.mkdir(pdf_dir)

# TODO maybe just use u.matshow? or does that do enough extra stuff that it
# would be hard to get it to just do what i want in this linearity-checking
# case?
# TODO factor this functionality into u.matshow if i end up using that
def matshow(ax, data, as_row=False, **kwargs):
    if len(data.shape) == 1:
        if as_row:
            ax_idx = 0
        else:
            ax_idx = -1
        data = np.expand_dims(data, -1)
    return ax.matshow(data, **kwargs)


# TODO maybe move into loop so it gets fname as a closure?
def savefigs(fig, prefix, fname):
    if prefix is not None:
        assert not prefix.endswith('_')
        prefix = prefix + '_'
    else:
        prefix = ''

    fig.savefig(join(fig_dir, 'png', prefix + fname + '.png'))
    #fig.savefig(join(fig_dir, 'svg', prefix + fname + '.svg'))
    fig.savefig(join(fig_dir, 'pdf', prefix + fname + '.pdf'))


def component_sum_error(weights, components, mix):
    component_sum = (weights * components.T).sum(axis=1)
    return np.linalg.norm(component_sum - mix)**2


def odor_and_fit_plot(odor_cell_stats, weighted_sum, ordered_cells, fname,
    title, odor_labels, cbar_label):

    f3, f3_axs = plt.subplots(1, 2, figsize=(10, 20), gridspec_kw={
        'wspace': 0,
        # assuming only output of imshow filled ax, this would seem to
        # be correct, but the column in the right axes seemed to small...
        #'width_ratios': [1, 1 / (len(odor_cell_stats.index.unique()) + 1)]
        # this might not be **exactly** right either, but pretty close
        'width_ratios': [1, 1 / len(odor_cell_stats.index.unique())]
    })
    cells_odors_and_fit = odor_cell_stats.loc[:, ordered_cells].T.copy()
    fit_name = 'WEIGHTED SUM'
    cells_odors_and_fit[fit_name] = weighted_sum[ordered_cells]
    labels = [x for x in odor_labels] + [fit_name]
    ax = f3_axs[0]

    xtickrotation = 'horizontal'
    fontsize = 8

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('left', size='3%', pad=0.5)

    im = u.matshow(cells_odors_and_fit, xticklabels=labels,
        xtickrotation=xtickrotation, fontsize=fontsize,
        title=title, ax=f3_axs[0])
    # Default is 'equal'
    ax.set_aspect('auto')

    f3.colorbar(im, cax=cax)
    cax.yaxis.set_ticks_position('left')
    cax.yaxis.set_label_position('left')
    cax.set_ylabel(cbar_label)

    ax = f3_axs[1]
    divider = make_axes_locatable(ax)
    cax2 = divider.append_axes('right', size='20%', pad=0.08)

    mix = odor_cell_stats.loc['mix']
    weighted_mix_diff = mix - weighted_sum
    im2 = matshow(ax, weighted_mix_diff[ordered_cells], cmap='coolwarm',
        aspect='auto')

    # move to right if i want to keep the y ticks
    ax.set_yticks([])
    ax.set_xticks([0])
    ax.set_xticklabels(['mix - sum'], fontsize=fontsize,
        rotation=xtickrotation)
    ax.tick_params(bottom=False)

    f3.colorbar(im2, cax=cax2)
    diff_cbar_label = r'$\frac{\Delta F}{F}$ difference'
    cax2.set_ylabel(diff_cbar_label)

    savefigs(f3, 'odorandfit', fname)


# TODO add appropriately formatted descrip of mix to input index cols so it can
# be used in plotting
def plot_pca(df, fname=None):
    pca_unstandardized = True
    if pca_unstandardized:
        pca_2 = PCA(n_components=2)
        pca_data = pca_2.fit_transform(df)

        pca_data = pd.DataFrame(index=df.index, data=pca_data)
        pca_data.rename(columns={0: 'PC1', 1: 'PC2'}, inplace=True)

        f1a = plt.figure()
        sns.scatterplot(data=pca_data.reset_index(), x='PC1', y='PC2',
            hue='name1', legend='full')
        #    hue='sample_type', style='fermented', size='day', legend='full')
        plt.title('PCA on raw data')

        pca_obj = PCA()
        pca_obj.fit(df)

        f1b = plt.figure()
        # TODO is explained_variance_ratio_ what i want exactly?
        plt.plot(pca_obj.explained_variance_ratio_[:15], 'k.')
        plt.title('PCA on raw data')
        plt.xlabel('Principal component')
        plt.ylabel('Fraction of explained variance')

        '''
        pc_df = pd.DataFrame(columns=df.columns,
                             data=pca_obj.components_)

        ###pc_df.rename(columns=fmt_chem_id, inplace=True)
        ###pc_df.columns.name = 'Chemical'
        for pc in range(2):
            print('Unstandardized PC{}:'.format(pc))
            # TODO check again that this is doing what i want
            # (factor to fn too)
            print(pc_df.iloc[pc].abs().sort_values(ascending=False)[:10])
        '''

    standardizer = StandardScaler()
    df_standardized = standardizer.fit_transform(df)

    pca_obj = PCA()
    pca_obj.fit(df_standardized)

    pca_2 = PCA(n_components=2)
    pca_data = pca_2.fit_transform(df_standardized)

    for n in range(pca_2.n_components):
        assert np.allclose(pca_obj.components_[n], pca_2.components_[n])

    # From Wikipedia page on PCA:
    # "If there are n observations with p variables, then the number of
    # distinct principal components is min(n - 1, p)."
    assert len(df.columns) == pca_2.n_features_
    assert len(df.index) == pca_2.n_samples_

    pca_data = pd.DataFrame(index=df.index, data=pca_data)
    pca_data.rename(columns={0: 'PC1', 1: 'PC2'}, inplace=True)

    f2a = plt.figure()
    # TODO plot trajectories instead of using marker size to indicate time
    # point
    # TODO what about day? size? (saturation / alpha would be ideal i think)
    sns.scatterplot(data=pca_data.reset_index(), x='PC1', y='PC2',
        hue='name1', legend='full')
        #hue='sample_type', style='fermented', size='day')#, legend='full')

    plt.title('PCA on standardized data')
    # TODO save figure

    f2b = plt.figure()
    plt.plot(pca_obj.explained_variance_ratio_[:15], 'k.')
    plt.title('PCA on standardized data')
    plt.xlabel('Principal component')
    plt.ylabel('Fraction of explained variance')

    '''
    pc_df = pd.DataFrame(columns=df.columns, data=pca_obj.components_)
    ####pc_df.rename(columns=fmt_chem_id, inplace=True)
    ####pc_df.columns.name = 'Chemical'
    for pc in range(2):
        print('Standardized PC{}:'.format(pc))
        print(pc_df.iloc[pc].abs().sort_values(ascending=False)[:10])
    '''

    if fname is not None:
        savefigs(f1a, 'pca_unstandardized', fname)
        savefigs(f1b, 'skree_unstandardized', fname)
        savefigs(f2a, 'pca', fname)
        savefigs(f2b, 'skree', fname)


# TODO maybe try on random subsets of cells (realistic # that MBONs read out?)
# TODO TODO count mix as same class or not? both?
# how do shen et al. disentagle this again? their generalization etc figures?
# TODO TODO use metric other than AU(roc)C since imbalanced classes
# area under ~"precision-recall" curve?
def roc_analysis(window_trial_stats, reliable_responders, fname=None):
    # TODO maybe don't subset to "reliable" responders as shen et al do?
    # TODO maybe just two distributions, one for natural one control?
    odors = window_trial_stats.index.get_level_values('name1')
    df = window_trial_stats[odors != 'pfo'].reset_index()

    auc_dfs = []
    for segmentation in (True, False):
        for odor in df.name1.unique():
            if segmentation and (odor == 'mix' or odor == 'kiwi'):
                continue

            odor_reliable_responders = reliable_responders.loc[(odor,)]
            odor_reliable_cells = odor_reliable_responders[
                odor_reliable_responders].index

            cells = []
            aucs = []
            for gn, gdf in df[df.cell.isin(odor_reliable_cells)
                ].groupby('cell'):

                if segmentation:
                    gdf = gdf[gdf.name1 != 'kiwi']

                if segmentation:
                    labels = (gdf.name1 == 'mix') | (gdf.name1 == odor)
                else:
                    labels = gdf.name1 == odor

                scores = gdf.df_over_f
                fpr, tpr, thresholds = roc_curve(labels, scores)
                curr_auc = auc(fpr, tpr)
                cells.append(gn)
                aucs.append(curr_auc)

            auc_dfs.append(pd.DataFrame({
                'task': 'segmentation' if segmentation else 'discrimination',
                'odor': odor,
                'cell': cells,
                'auc': aucs
            }))

            fig = plt.figure()
            plt.hist(aucs, range=(0,1))
            plt.axvline(x=0.5, color='r')
            # TODO TODO TODO add stuff to identify recording to titles
            if segmentation:
                plt.title('AUC distribution, segmentation for {}'.format(odor))
            else:
                plt.title('AUC distribution, {} vs all discrimination'.format(
                    odor))

            if fname is not None:
                odor_fname = odor.replace(' ', '_')
                task_fname = 'seg' if segmentation else 'discrim'

                savefigs(fig, None, fname + '_' + odor_fname + '_' + task_fname)

    # TODO maybe also plot average distributions for segmentation and
    # discrimination, within this fly, but across all odors?
    # (if so, should odors be weighted equally, or should each cell (of which
    # some odors will have less b/c less reliable responders)?)

    # TODO also return auc values (+ n cells used in each case?) for
    # analysis w/ data from other flies (n cells in current return output?)
    auc_df = pd.concat(auc_dfs, ignore_index=True)
    return auc_df


cell_cols = ['name1','name2','repeat_num','cell']

outputs_pickle_fstr = 'kc_mix_analysis_outputs_meanzthr{:.2f}.p'
analyze_cached_outputs = True
#analyze_cached_outputs = False
if not analyze_cached_outputs:
    mean_zchange_response_thresh = 3.0
    # TODO use a longer/shorter baseline window?
    baseline_start = -2
    baseline_end = 0
    response_start = 0
    response_calling_s = 5.0

    # TODO TODO update loop to use this df, and get index values directly from
    # there, rather than re-calculating them
    latest_pickles = u.latest_trace_pickles()
    pickles = list(latest_pickles.trace_pickle_path)

    if test:
        warnings.warn('Only reading one pickle for testing! ' +
            'Set test = False to analyze all.')
        pickles = [p for p in pickles if '08-27_9_fn_0001' in p]
        #pickles = [p for p in pickles if '08-27_9' in p]

    # TODO maybe use for this everything to speed things up a bit?
    # (not just plotting)
    # this seemed to yield *intermittently* clean looking plots,
    # even within a single experiment
    #plotting_td = pd.Timedelta(0.5, unit='s')
    # both of these still making spiky plots... i feel like something might be
    # up
    #plotting_td = pd.Timedelta(1.0, unit='s')
    #plotting_td = pd.Timedelta(2.0, unit='s')

    # TODO TODO TODO why does it seem that, almost no matter the averaging
    # window, there is almost identical up-and-down noise for a large fraction
    # of traces????
    max_plotting_td = 1.0

    responder_dfs = []
    auc_dfs = []
    for df_pickle in pickles:
        # TODO also support case here pickle has a dict
        # (w/ this df behind a trace_df key & maybe other data, like PID, behind
        # something else?)
        df = pd.read_pickle(df_pickle)
        # TODO resolve whatever caused recording_from to get split into _x and
        # _y cols (seems to be same values though)

        assert 'original_name1' in df.columns
        df.name1 = df.original_name1.map(cu.odor2abbrev)

        # TODO delete
        '''
        if 'original_name1' in df.columns:
            df.name1 = df.original_name1.map(odor2abbrev)

        # TODO fix that data output s.t. it has original name and delete this
        # and other stuff back translating from case specific abbreviations
        else:
            assert '/20190815_' in df_pickle
            corrected = False
            for n, corr in key_corrs.items():
                if df_pickle.endswith('_00{}.p'.format(n)):
                    df.name1 = df.name1.map(corr)
                    assert not pd.isnull(df.name1).any()
                    corrected = True
                    break
            assert corrected
        '''
        prefix = u.df_to_odorset_name(df)
        odor_order = [cu.odor2abbrev(o) for o in u.df_to_odor_order(df)]
        
        parts = df_pickle[:-2].split('_')[-4:]
        title = '/'.join([parts[0], parts[1], '_'.join(parts[2:])])
        fname = prefix.replace(' ','') + '_' + title.replace('/','_')
        title = prefix.title() + ': ' + title

        print(fname)

        # TODO maybe convert other handling of from_onset to timedeltas?
        # (also for ease of resampling / using other time based ops)
        #in_response_window = ((df.from_onset > 0.0) &
        #                      (df.from_onset <= response_calling_s))
        df.from_onset = pd.to_timedelta(df.from_onset, unit='s')
        in_response_window = (
            (df.from_onset > pd.Timedelta(response_start, unit='s')) &
            (df.from_onset <= pd.Timedelta(response_start + response_calling_s,
                unit='s'))
        )

        window_df = df.loc[in_response_window,
            cell_cols + ['order','from_onset','df_over_f']]
        window_df.set_index(cell_cols + ['order','from_onset'], inplace=True)

        window_by_trial = window_df.groupby(cell_cols + ['order'])['df_over_f']

        in_baseline_window = (
            (df.from_onset >= pd.Timedelta(baseline_start, unit='s')) &
            (df.from_onset <= pd.Timedelta(baseline_end, unit='s')))

        # TODO move below response calling if not going to use for that...
        stat = 'max'
        if stat == 'max':
            window_trial_stats = window_by_trial.max()
        elif stat == 'mean':
            window_trial_stats = window_by_trial.mean()
        #

        baseline_df = df.loc[in_baseline_window,
            cell_cols + ['order','from_onset','df_over_f']]
        baseline_by_trial = baseline_df.groupby(cell_cols + ['order']
            )['df_over_f']

        # TODO TODO speed up this standardization process somehow?
        print('standardizing...', end='', flush=True)
        # TODO could just groupby once and then pass multiple functions to
        # agg?
        baseline_stddev = baseline_by_trial.std()
        baseline_mean = baseline_by_trial.mean()
        response_criteria = pd.Series(index=window_df.index)
        # TODO maybe z change should be computed from raw f rather than dff?
        # just calc ratio over stddev with this metric?
        for gn, gdf in window_df.groupby(cell_cols + ['order']):
            zchange = ((gdf.df_over_f - baseline_mean.loc[gn]) /
                baseline_stddev.loc[gn])
            response_criteria.loc[gn] = zchange
        print(' done')

        if responder_threshold_plots:
            zthreshes = np.linspace(0, 25.0, 40)
            resp_frac_over_zthreshes = np.empty_like(zthreshes) * np.nan
            mean_rc = response_criteria.groupby(cell_cols).agg('mean')
            # TODO for all odors? specific reference odors?) [-> pick threshold
            # from there?]
            for i, z_thr in enumerate(zthreshes):
                z_thr_trial_responders = mean_rc >= z_thr
                frac = \
                    z_thr_trial_responders.sum() / len(z_thr_trial_responders)

                resp_frac_over_zthreshes[i] = frac

            thr_fig, thr_ax = plt.subplots()
            thr_ax.plot(zthreshes, resp_frac_over_zthreshes)
            thr_ax.set_title(title + ', response threshold sensitivity')
            thr_ax.set_xlabel('Mean Z-scored response threshold')
            thr_ax.set_ylabel('Fraction of cells responding (across all odors)')
            # TODO maybe draw vertical line at 10% and annotate w/ val?
            # TODO vertical line at whatever fixed threshold is, if using one?
            # (annotated w/ responder fraction there)
            # TODO maybe pick thresh from some kind of max of derivative (to
            # find an elbow)?
            # TODO or just use on one / a few flies for tuning, then disable?
            savefigs(thr_fig, 'threshold_sensitivity', fname)

        print('calling responders...', end='', flush=True)
        # TODO not sure why it seems i need such a high threshold here, to get
        # reasonable sparseness... was the fly i'm testing it with just super
        # responsive?
        trial_responders = (response_criteria.groupby(cell_cols).agg('mean') >
            mean_zchange_response_thresh)
        print(' done')

        print(('Fraction of cells trials counted as responses (mean z-scored '
            'dff > {:.2f}): {:.2f}').format(mean_zchange_response_thresh, 
            trial_responders.sum() / len(trial_responders)))

        '''
        # TODO TODO should i sort input data so natural stuff is always analyzed
        # first, if i want to use one of those odors to pick threshold? or have
        # a separate reference odor for the other set (should give similar
        # thresholds within fly, right?) or should i just not do it this way
        # anyway...?

        # These ref odors + fracs taken from 0.7 thresh on 2019-8-27/9 fly
        if prefix == 'kiwi':
            ref_odor = 'eb'
            ref_response_percent = 18.6
        else:
            ref_odor = '1o3ol'
            ref_response_percent = 11.1

        max_responder_thresh = np.percentile(
            window_by_trial.max().loc[(ref_odor,)],
            100 - ref_response_percent
        )
        # TODO where thresh came from
        print('max_responder_thresh from ref odors: {:.2f}'.format(
            max_responder_thresh))

        trial_responders = window_by_trial.max() > max_responder_thresh

        # TODO exclude pfo for this and below? (probably for reported means)
        print(('Fraction of cells trials counted as responses (max dff > {}): '
            '{:.3f}').format(max_responder_thresh, 
            trial_responders.sum() / len(trial_responders)))
        '''
        # TODO deal w/ case where there are only 2 repeats (shouldn't the number
        # be increased by fraction expected to respond if given a 3rd trial?)
        # ...or just get better data and ignore probably
        # As >= 50% response to odor criteria in Shen paper
        reliable_responders = \
            trial_responders.groupby(['name1','cell']).sum() >= 2

        print(('Mean fraction of cells responding to at least 2/3 trials:'
            ' {:.3f}').format(
            reliable_responders.sum() / len(reliable_responders)))

        n_cells = len(df.cell.unique())
        print('Fraction of cells responding to each trial of each odor:')
        # TODO TODO is the population becoming silent to kiwi more quickly? is
        # that consistent?
        frac_odor_trial_responders = trial_responders.groupby(
            ['name1','repeat_num']).sum() / n_cells

        print(frac_odor_trial_responders.to_string(float_format='%.3f'))

        mean_frac_odor_responders = \
            frac_odor_trial_responders.groupby('name1').mean()

        print('Mean fraction of cells responding to each odor:')
        print(mean_frac_odor_responders.to_string(float_format='%.3f'))
        # TODO TODO also concat these responder fraction things across flies
        # w/ appropriate index info -> make plots after loop over data

        # TODO also breakdown reliable by odor?

        auc_df = roc_analysis(window_trial_stats, reliable_responders,
            fname=fname)

        def get_single_index_val(var):
            values  = df[var].unique()
            assert len(values) == 1
            return values[0]

        def add_metadata(out_df):
            keys_to_add = ['prep_date', 'fly_num', 'thorimage_id']
            vals_to_add = [get_single_index_val(k) for k in keys_to_add]
            # TODO maybe delete this df special case. series case may work fine
            # for dfs too.
            if len(out_df.shape) > 1:
                for k, v in zip(keys_to_add, vals_to_add):
                    out_df[k] = v
            else:
                # TODO i thought this would be the one line way to do it, but i
                # guess not... is there one?
                #out_df = pd.concat([out_df], names=keys_to_add,
                #    keys=vals_to_add)
                for k, v in zip(keys_to_add[::-1], vals_to_add[::-1]):
                    out_df = pd.concat([out_df], names=[k], keys=[v])

            return out_df

        responder_dfs.append(add_metadata(trial_responders))
        auc_dfs.append(add_metadata(auc_df))

        """
        # TODO special handling for real kiwi in this section?

        # TODO more idiomatic way?
        # may want a table output? or a series of bar graphs?
        odors = [x for x in
            trial_responders.index.get_level_values('name1').unique()
            if x != 'pfo'
        ]

        odor_resp_subset_fracs_list = []
        for odor in odors:
            oresp = reliable_responders.loc[odor]
            cells = oresp[oresp].index.get_level_values('cell').unique()

            n_odor_cells = len(cells)

            other_odors = [o for o in odors if o != odor]
            # TODO or maybe use reliable responders here too?
            # TODO breakdown by trial as well
            resp_fracs_to_others = trial_responders.loc[other_odors, :, :, cells
                ].groupby('name1').sum() / (n_odor_cells * 3)
            # TODO revisit (something more clear?)
            resp_fracs_to_others.name = 'of_' + odor + '_resp'

            odor_resp_subset_fracs_list.append(resp_fracs_to_others)

        odor_resp_subset_fracs = pd.concat(odor_resp_subset_fracs_list, axis=1,
            sort=False)

        # TODO print the above in some nice(r) way?
        # TODO TODO or save to figure? (like df_to_image?)
        print('Responder fractions to subset of cells responding reliably'
            ' to each odor:')
        print(odor_resp_subset_fracs)
        print('')

        # TODO include mix?
        # TODO exclude pfo
        n_ro_hist_fig = plt.figure()
        reliable_responders.groupby('cell').sum().hist()
        # TODO oo approach? from ret above? def ax first?
        ax = plt.gca()
        ax.set_title(title + ', number of odors cells respond reliably to')
        savefigs(n_ro_hist_fig, 'n_ro_hist', fname)
        """

        """
        do_pca = True
        if do_pca:
            pivoted_window_trial_stats = pd.pivot_table(
                window_trial_stats.to_frame(name=stat), columns='cell',
                index=['name1','name2','repeat_num'], values=stat
            )
            # TODO TODO add stuff to identify recording to titles
            plot_pca(pivoted_window_trial_stats, fname=fname)

        responsiveness = window_trial_stats.groupby('cell').mean()
        cellssorted = responsiveness.sort_values(ascending=False)

        top_n = 100
        order = cellssorted.index

        trial_by_cell_stats = window_trial_stats.to_frame().pivot_table(
            index=['name1','name2','repeat_num','order'],
            columns='cell', values='df_over_f')

        # TODO maybe also add support for single letter abbrev case
        # (as was handled w/ commented sort stuff below)
        trial_by_cell_stats = \
            trial_by_cell_stats.reindex(odor_order, level='name1')

        #trial_by_cell_stats.sort_index(level='name1', sort_remaining=False,
        #    inplace=True)

        if trial_matrices:
            trial_by_cell_stats_top = trial_by_cell_stats.loc[:, order[:top_n]]

            cbar_label = stat.title() + r' response $\frac{\Delta F}{F}$'

            odor_labels = u.matlabels(trial_by_cell_stats_top, u.format_mixture)
            # TODO fix x/y in this fn... seems T required
            f1 = u.matshow(trial_by_cell_stats_top.T, xticklabels=odor_labels,
                group_ticklabels=True, colorbar_label=cbar_label, fontsize=6,
                title=title)
            ax = plt.gca()
            ax.set_aspect(0.1)
            savefigs(f1, 'trials', fname)

        odor_cell_stats = trial_by_cell_stats.groupby('name1').mean()
        # TODO TODO factor linearity checking in kc_analysis to use this,
        # since A+B there is pretty much a subset of this case
        # (-> hong2p.util, both use that?)

        # TODO TODO check kiwi and pfo are excluded from fit
        component_names = [x for x in odor_cell_stats.index
            if x not in ('mix', 'kiwi', 'pfo')] 
        # TODO also do on traces as in kc_analysis?
        # or at least per-trial rather than per-mean?

        # TODO delete try/except
        try:
            mix = odor_cell_stats.loc['mix']
        except KeyError:
            import ipdb; ipdb.set_trace()

        components = odor_cell_stats.loc[component_names]
        component_sum = components.sum()
        assert mix.shape == component_sum.shape

        mix_norm = np.linalg.norm(mix)
        component_sum_norm = np.linalg.norm(component_sum)

        scaled_sum = (mix_norm / component_sum_norm) * component_sum
        scaled_sum_norm = np.linalg.norm(scaled_sum)
        assert np.isclose(scaled_sum_norm, mix_norm), '{} != {}'.format(
            scaled_sum_norm, mix_norm)

        scaled_sum_mix_diff = mix - scaled_sum
        # A: of dimensions (M, N)
        # B: of dimensions (M,)
        a = components.T
        b = mix
        try:
            # TODO worth also contraining coeffs to sum to 1 or something?
            # / be non-neg? and how?
            coeffs, residuals, rank, svs = np.linalg.lstsq(a, b, rcond=None)
            # TODO any meaning to svs? worth checking anything about that or
            # rank?
        except np.linalg.LinAlgError as e:
            raise

        # TODO maybe print the coefficients (or include on plot?)?
        weighted_sum = (coeffs * a).sum(axis=1)
        weighted_mix_diff = mix - weighted_sum
        assert np.isclose(residuals[0], np.linalg.norm(mix - weighted_sum)**2)
        assert np.isclose(residuals[0],
            component_sum_error(coeffs, components, mix))

        # Just since we'd expect the model w/ more parameters to do better,
        # given it's actually optimizing what we want.
        assert (np.linalg.norm(weighted_mix_diff) <
                np.linalg.norm(scaled_sum_mix_diff)), 'lstsq did no better'

        # This was to check that lstsq was doing what I wanted (and it seems to
        # be), but it could also be used to introduce constraints.
        '''
        x0 = coeffs.copy()
        res0 = minimize(component_sum_error, x0, args=(components, mix))
        x0 = np.ones(components.shape[0]) / components.shape[0]
        res1 = minimize(component_sum_error, x0, args=(components, mix))
        '''

        if fit_matrices:
            diff_fig, diff_axs = plt.subplots(2, 2, sharex=True, sharey=True)
            ax = diff_axs[0, 0]

            #aspect_one_col = 0.05 #0.1
            aspect_one_col = 'auto'
            title_rotation = 0 #90
            # TODO delete after figuring out spacing
            titles = False
            #

            matshow(ax, scaled_sum[order[:top_n]], aspect=aspect_one_col)
            #ax.matshow(scaled_sum, vmin=vmin, vmax=vmax,
            #           extent=[xmin,xmax,ymin,ymax], aspect='auto')

            ax.set_xticks([])
            ax.set_yticks([])
            #
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            #
            if titles:
                ax.set_title('Scaled sum of monomolecular responses',
                    rotation=title_rotation)

            ax = diff_axs[0, 1]
            # TODO TODO appropriate vmin / vmax here?
            # [-1, 1] or maybe [-1.5, 1.5] would seem to work ok..?
            # TODO share a colorbar between the two difference plots?
            # (if fixed range, would seem reasonable)
            mat = matshow(ax, scaled_sum_mix_diff[order[:top_n]],
                aspect=aspect_one_col, cmap='coolwarm')
            #mat = matshow(ax, scaled_sum_mix_diff,
            #    extent=[xmin,xmax,ymin,ymax], aspect='auto', cmap='coolwarm')
            # TODO why this not seem to be working?
            diff_fig.colorbar(mat, ax=ax)

            if titles:
                ax.set_title('Mixture response - scaled sum',
                    rotation=title_rotation)
            # TODO probably change from responder_traces... fn? use u.matshow?
            #ax.set_xlabel(responder_traces.columns.name)
            #ax.set_ylabel(responder_traces.index.name)
            ax.yaxis.set_ticks_position('right')
            ax.xaxis.set_ticks_position('bottom')
            #
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            #

            ax = diff_axs[1, 0]
            #matshow(ax, weighted_sum, vmin=vmin, vmax=vmax,
            #    extent=[xmin,xmax,ymin,ymax], aspect='auto')
            matshow(ax, weighted_sum[order[:top_n]], aspect=aspect_one_col)
            ax.set_xticks([])
            ax.set_yticks([])
            #
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            #
            if titles:
                ax.set_title('Weighted sum', rotation=title_rotation)

            ax = diff_axs[1, 1]
            #mat2 = matshow(ax, weighted_mix_diff, extent=[xmin,xmax,ymin,ymax],
            #    aspect='auto', cmap='coolwarm')
            mat2 = matshow(ax, weighted_mix_diff[order[:top_n]],
                aspect=aspect_one_col, cmap='coolwarm')
            diff_fig.colorbar(mat2, ax=ax)

            if titles:
                ax.set_title('Mixture response - weighted sum',
                    rotation=title_rotation)
            #ax.set_xlabel(responder_traces.columns.name)
            #ax.set_ylabel(responder_traces.index.name)
            ax.yaxis.set_ticks_position('right')
            ax.xaxis.set_ticks_position('bottom')
            #
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            #

            diff_fig.subplots_adjust(wspace=0)
            #diff_fig.tight_layout(rect=[0, 0, 1, 0.9])
            '''
            diff_fig_path = 
            diff_fig.savefig(diff_fig_path)
            '''

        cbar_label = 'Mean ' + stat + r' response $\frac{\Delta F}{F}$'
        odor_cell_stats_top = odor_cell_stats.loc[:, order[:top_n]]
        odor_labels = u.matlabels(odor_cell_stats_top, u.format_mixture)

        if odor_matrices:
            # TODO TODO modify u.matshow to take a fn (x/y)labelfn? to generate
            # str labels from row/col indices
            f2 = u.matshow(odor_cell_stats_top.T, xticklabels=odor_labels,
                colorbar_label=cbar_label, fontsize=6, title=title)
            ax = plt.gca()
            ax.set_aspect(0.1)
            savefigs(f2, 'avg', fname)

        if odor_and_fit_matrices:
            odor_and_fit_plot(odor_cell_stats, weighted_sum, order[:top_n],
                fname, title, odor_labels, cbar_label)

        # TODO TODO TODO one plot with avg_traces across flies, w/ hue maybe
        # being the fly
        if avg_traces:
            frame_delta = df.from_onset.diff().median().total_seconds()
            # To deal w/ extra samples sometimes getting picked up, going to
            # decrease the downsampling factor by an amount that won't equal
            # a new timedelta after multiplied by max frames per trial.
            max_n_frames = df.groupby(cell_cols).size().max()
            plot_ds_factor = (np.floor(max_plotting_td / frame_delta) - 
                frame_delta / (max_n_frames + 1))
            plotting_td = pd.Timedelta(plot_ds_factor * frame_delta, unit='s')
            print('median frame_delta:', frame_delta)
            print('plot_ds_factor:', plot_ds_factor)
            print('plotting_td:', plotting_td)
            '''

            # TODO could also using rolling window if just wanting it to look
            # more smooth, rather than actually have less points
            start = time.time()
            resampler = df.groupby(cell_cols)[['from_onset','df_over_f']
                ].resample(plotting_td, on='from_onset')
            downsampled_df = resampler.median().reset_index()
            print('pure downsampling took {:.3f}s'.format(time.time() - start))
            '''

            #start = time.time()
            #smoothed_df = df.copy()
            #smoothed_df = downsampled_df.copy()
            #smoothing_td = 2 * plotting_td

            '''
            smoothing_td = pd.Timedelta(2.0, unit='s')
            # no matter as_index+group_keys=False, there is still another level
            # added to index... this just how it works?
            smoothed_df_over_f = smoothed_df.groupby(cell_cols, sort=False,
                as_index=False, group_keys=False)[['from_onset','df_over_f']
                ].rolling(smoothing_td, on='from_onset').mean(
                ).df_over_f.reset_index(level=0, drop=True)
            '''
            '''
            smoothing_iterations = 10
            smoothing_window_size = 10
            smoothing_td = pd.Timedelta(smoothing_window_size * frame_delta,
                unit='s')
            for _ in range(smoothing_iterations):
                smoothed_df.df_over_f = smoothed_df.groupby(cell_cols,
                    sort=False, as_index=False, group_keys=False
                    ).df_over_f.rolling(smoothing_window_size).mean(
                    ).reset_index(level=0, drop=True)

                smoothed_df.from_onset = \
                    smoothed_df.from_onset - smoothing_td / 2

            smoothed_df.from_onset = smoothed_df.from_onset.apply(
                lambda x: x.total_seconds())
            '''
            avg_df = df.groupby(cell_cols[:-1] + ['from_onset']).mean(
                ).reset_index()

            smoothed_df = avg_df.copy()
            smoothing_window_size = 7
            smoothing_td = pd.Timedelta(smoothing_window_size * frame_delta,
                unit='s')
            smoothed_df.df_over_f = smoothed_df.groupby(cell_cols, sort=False,
                as_index=False, group_keys=False).df_over_f.rolling(
                smoothing_window_size).mean().reset_index(level=0, drop=True)

            smoothed_df.from_onset = smoothed_df.from_onset - smoothing_td / 2

            '''
            resampler = smoothed_df.groupby(cell_cols)[['from_onset',
                'df_over_f']].resample(plotting_td, on='from_onset')

            smoothed_df = resampler.mean().reset_index()
            '''

            '''
            smoothed_df_over_f = smoothed_df.groupby(cell_cols, sort=False,
                as_index=False, group_keys=False).df_over_f.apply(lambda ts:
                pd.Series(index=ts.index, data=u.smooth(ts, window_len=30))
                ).reset_index(level=0, drop=True)
            smoothed_df.df_over_f = smoothed_df_over_f 
            '''

            '''
            smoothed_downsampled_df = smoothed_df.groupby(cell_cols)[
                ['from_onset','df_over_f']].resample(plotting_td,
                on='from_onset').mean().reset_index()

            print('smoothing downsampling took {:.3f}s'.format(
                time.time() - start))
            '''
            '''
            start = time.time()
            g = sns.relplot(data=df, x='from_onset', y='df_over_f',
                col='name1', col_order=odor_order, kind='line', ci=None,
                color='black')
            print('plotting raw took {:.3f}s'.format(time.time() - start))
            '''

            # TODO maybe re-enable ci after downsampling
            g = sns.relplot(data=smoothed_df,
                x='from_onset', y='df_over_f',
                col='name1', col_order=odor_order, kind='line', ci=None,
                color='black', alpha=0.7)
            #, linewidth=0.5)
            #, hue='repeat_num')
            #print('plotting downsampled took {:.3f}s'.format(
            #    time.time() - start))
            g.set_titles('{col_name}')
            g.fig.suptitle('Average trace across all cells, ' +
                title[0].lower() + title[1:])

            g.axes[0,0].set_xlabel('Seconds from onset')
            g.axes[0,0].set_ylabel(r'Mean $\frac{\Delta F}{F}$')
            for a in g.axes.flat[1:]:
                a.axis('off')

            g.fig.subplots_adjust(top=0.9, left=0.05)
            savefigs(g.fig, 'avg_traces', fname)

        # TODO TODO TODO plot pid too

        # TODO another flag for this part?
        for odor in odor_cell_stats.index:
            # TODO maybe put all sort orders in one plot as subplots?
            order = \
                odor_cell_stats.loc[odor, :].sort_values(ascending=False).index

            sort_odor_labels = [o + ' (sorted)' if o == odor else o
                for o in odor_labels]
            ss = '_{}_sorted'.format(odor)

            # TODO TODO TODO here and in plots that also have fits, show (in
            # general, nearest?  est? scalar magnitude of one of these?) eag +
            # in roi / full frame MB fluorescence under each column?
            if odor_matrices:
                odor_cell_stats_top = odor_cell_stats.loc[:, order[:top_n]]
                fs = u.matshow(odor_cell_stats_top.T,
                    xticklabels=sort_odor_labels, colorbar_label=cbar_label,
                    fontsize=6, title=title)
                ax = plt.gca()
                ax.set_aspect(0.1)
                savefigs(fs, 'avg', fname + ss)

            if odor_and_fit_matrices:
                odor_and_fit_plot(odor_cell_stats, weighted_sum, order[:top_n],
                    fname + ss, title, sort_odor_labels, cbar_label)
        """
        print('\n')

    # This has a meaningful index.
    responder_df = pd.concat(responder_dfs)
    # This does not (just a RangeIndex).
    auc_df = pd.concat(auc_dfs, ignore_index=True)

    # TODO symlink kc_mix_analysis_output.p to most recent? or just load most
    # recent by default?
    # Including threshold in name, so that i can try responder based analysis on
    # output calculated w/ multiple thresholds, w/o having to wait for slow
    # re-calculation.
    outputs_pickle_name = outputs_pickle_fstr.format(
        mean_zchange_response_thresh)

    with open(outputs_pickle_name, 'wb') as f:
        data = {
            'mean_zchange_response_thresh': mean_zchange_response_thresh,
            'baseline_start': baseline_start,
            'baseline_end': baseline_end,
            'response_start': response_start,
            'response_calling_s': response_calling_s,

            'responder_df': responder_df,
            'auc_df': auc_df,
        }
        pickle.dump(data, f)

else:
    desired_thr = 2.5
    outputs_pickle_name = outputs_pickle_fstr.format(desired_thr)
    with open(outputs_pickle_name, 'rb') as f:
        data = pickle.load(f)

    mean_zchange_response_thresh = data['mean_zchange_response_thresh']
    baseline_start = data['baseline_start']
    baseline_end = data['baseline_end']
    response_start = data['response_start']
    response_calling_s = data['response_calling_s']

    auc_df = data['auc_df']
    responder_df = data['responder_df']

# TODO TODO TODO across fly responder based analysis

# TODO TODO TODO some kind of plot of the correlations themselves, to make a
# statement across flies?

fly_keys = ['prep_date','fly_num']
rec_key = 'thorimage_id'
n_flies = len(responder_df.index.to_frame()[fly_keys].drop_duplicates())
fly_colors = sns.color_palette('hls', n_flies)
# could also try ':' or '-.'
odorset2linestyle = {'kiwi': '-', 'control': '--'}

n_ro_hist_fig, n_ro_hist_ax = plt.subplots()
# Only the last bin includes both ends. All other bins only include the
# value at their left edge. So with n_odors + 2, the last bin will be
# [n_odors, n_odors + 1] (since arange doesn't include end), and will thus
# only count cells that respond (reliably) to all odors, since it is not
# possible for them to respond to > n_odors.
n_odors = 6
n_ro_bins = np.arange(n_odors + 2)

for i, (fly_gn, fly_gser) in enumerate(responder_df.groupby(fly_keys)):
    fly_color = fly_colors[i]

    assert len(fly_gser.index.get_level_values(rec_key).unique()) == 2
    # TODO TODO TODO just add variable for odorset earlier, so that i can group
    # on that instead of (/in addition to) thorimage id, so i can loop over them
    # in a fixed order
    for rec_gn, rec_gser in fly_gser.groupby(rec_key):
        # TODO maybe refactor this (kinda duped w/ odorset finding from the more
        # raw dfs)?
        if 'eb' in rec_gser.index.get_level_values('name1'):
            odorset = 'kiwi'
        else:
            odorset = 'control'
        linestyle = odorset2linestyle[odorset]

        label = (odorset + ', ' +
            fly_gn[0].strftime(u.date_fmt_str) + '/' + str(fly_gn[1]))
        # TODO include thorimage id anyway?
        fname = label.replace(',','').replace(' ','_').replace('/','_')

        trial_responders = rec_gser
        # TODO probably delete this. i want to be able to plot pfo + kiwi
        # response fractions / reliable response fraction in one set of plots.
        # at least save as a redefinition for below.
        #trial_responders = rec_gser[~ rec_gser.index.get_level_values('name1'
        #    ).isin(('pfo', 'kiwi'))]

        n_rec_cells = \
            len(trial_responders.index.get_level_values('cell').unique())

        # TODO TODO dedupe this section with above (just do here?)
        ########################################################################
        # TODO deal w/ case where there are only 2 repeats (shouldn't the number
        # be increased by fraction expected to respond if given a 3rd trial?)
        # ...or just get better data and ignore probably
        # As >= 50% response to odor criteria in Shen paper
        reliable_responders = \
            trial_responders.groupby(['name1','cell']).sum() >= 2

        frac_reliable_responders = \
            reliable_responders.groupby('name1').sum() / n_rec_cells

        # TODO TODO try to consolidate this w/ odor_order (they should have
        # the same stuff, just one also has order info, right?)
        odors = [x for x in
            trial_responders.index.get_level_values('name1').unique()]

        full_odor_order = [cu.odor2abbrev(o) for o in u.odor_set2order[odorset]]
        seen_odors = set()
        odor_order = []
        for o in full_odor_order:
            if o not in seen_odors and o in odors:
                seen_odors.add(o)
                odor_order.append(o)

        # TODO TODO TODO TODO check that we are not getting wrong results by
        # dividing by 3 anywhere when the odor is actually only recorded twice
        # (count unique repeat_num?) (check above too!) (i think i might have
        # handled it correctly here...)
        n_odor_repeats = trial_responders.reset_index().groupby('name1'
            ).repeat_num.nunique()

        frac_responders = (trial_responders.groupby('name1').sum() /
            (n_odor_repeats * n_rec_cells))[odor_order]
        resp_frac_fig = plt.figure()
        resp_frac_ax = frac_responders.plot.bar(color='black')
        resp_frac_ax.set_title(label.title() +
            '\nAverage fraction responding by odor')
        # TODO hide name1 xlabel before saveing each of these bar plots / 
        # change it to "Odor" or something
        savefigs(resp_frac_fig, 'resp_frac', fname)

        '''
        reliable_frac_fig = plt.figure()
        reliable_frac_ax = frac_reliable_responders[odor_order].plot.bar(
            color='black')
        reliable_frac_ax.set_title(label.title() +
            '\nReliable responder fraction by odor')
        savefigs(reliable_frac_fig, 'reliable_frac', fname)
        '''

        reliable_of_resp_fig = plt.figure()
        reliable_of_resp_ax = (frac_reliable_responders / frac_responders
            )[odor_order].plot.bar(color='black')
        reliable_of_resp_ax.set_title(label.title() +
            '\nFraction of responders that are reliable, by odor')
        savefigs(reliable_of_resp_fig, 'reliable_of_resp', fname)

        odors = [o for o in odors if o not in ('pfo', 'kiwi')]
        odor_order = [o for o in odor_order if o not in ('pfo', 'kiwi')]

        odor_resp_subset_fracs_list = []
        for odor in odors:
            oresp = reliable_responders.loc[odor]
            cells = oresp[oresp].index.get_level_values('cell').unique()

            n_odor_cells = len(cells)

            #other_odors = [o for o in odors if o != odor]
            other_odors = list(odors)

            '''
            # TODO or maybe use reliable responders here too?
            # (if not, there might actually be more cells that respond (on
            # average) to another odor, than to the odor for which they were
            # determined to be reliable responders)
            # TODO breakdown by trial as well?
            resp_fracs_to_others = trial_responders.loc[:, :, :, other_odors,
                :, :, cells ].groupby('name1').sum() / (n_odor_cells * 3)

            # TODO revisit (something more clear?)
            resp_fracs_to_others.name = 'of_' + odor + '_resp'

            odor_resp_subset_fracs_list.append(resp_fracs_to_others)
            '''
            norm_frac_reliable_to_others = False
            fracs_reliable_to_others = reliable_responders.loc[other_odors,
                cells].groupby('name1').sum() / n_odor_cells

            if norm_frac_reliable_to_others:
                fracs_reliable_to_others /= frac_reliable_responders
                # TODO TODO TODO does the weird value of the (mix, of_mix_resp)
                # (and other identities) mean that this normalization is not
                # meaningful? should i be doing something differently?

                # TODO maybe in the normed ones, just don't show mix thing,
                # since that value seems weird?

            fracs_reliable_to_others.name = 'of_' + odor + '_resp'

            odor_resp_subset_fracs_list.append(fracs_reliable_to_others)
        
        odor_resp_subset_fracs = pd.concat(odor_resp_subset_fracs_list, axis=1,
            sort=False)

        fig = plt.figure()
        of_mix_reliable_to_others = \
            odor_resp_subset_fracs['of_mix_resp'][odor_order]

        ax = of_mix_reliable_to_others.plot.bar(color='black')
        ax.set_title(label.title() + '\nFraction of mix reliable responders '
            'reliable to other odors')
        savefigs(fig, 'mix_rel_to_others', fname)

        of_mix_reliable_to_others_ratio = \
            of_mix_reliable_to_others / frac_reliable_responders

        # TODO see note above. excluding mix disingenuous?
        of_mix_reliable_to_others_ratio = \
            of_mix_reliable_to_others_ratio[[o for o in odor_order
            if o != 'mix']]
        assert 'mix' not in of_mix_reliable_to_others_ratio.index

        ratio_fig = plt.figure()
        ratio_ax = of_mix_reliable_to_others_ratio.plot.bar(color='black')
        ratio_ax.set_title(label.title() + '\nFraction of mix reliable'
            ' responders reliable to other odors (ratio)')
        savefigs(ratio_fig, 'ratio_mix_rel_to_others', fname)

        # TODO TODO TODO aggregate across flies somehow? points for each
        # fraction ratio? (swarm?) (mean frac at least?)

        # TODO TODO TODO still maybe show this as a matshow, since that seems to
        # be one version of the all-pairwise-venn-diagram thing betty was trying
        # to envision, right?
        '''
        # TODO print the above in some nice(r) way?
        # TODO TODO or save to figure? (like df_to_image?)
        print('Responder fractions to subset of cells responding reliably'
            ' to each odor:')
        print(odor_resp_subset_fracs)
        print('')
        '''

        # TODO maybe try w/ any responses counting it as a responder for the
        # odor, instead of the 2 required for reliable_responders?
        rec_n_reliable_responders = reliable_responders.groupby('cell').sum()

        # TODO maybe use kde instead?
        n_ro_hist_ax.hist(rec_n_reliable_responders, bins=n_ro_bins,
            density=True, histtype='step', color=fly_color, linestyle=linestyle,
            label=label)
        ########################################################################

n_ro_hist_ax.legend()
n_ro_hist_ax.set_title('Cell tuning breadth')
n_ro_hist_ax.set_xlabel('Number of odors cells respond to (at least twice)')
n_ro_hist_ax.set_ylabel('Fraction of cells')

savefigs(n_ro_hist_fig, None, 'n_ro_hist')

# TODO TODO TODO some kind of plot showing adaptation to each odor, to see if
# that thing i saw once to real kiwi (faster adaptation, i think) holds

plt.show()
import ipdb; ipdb.set_trace()

# TODO TODO some way to make a statement about the PCA stuff across flies?
# worth it?
# TODO TODO TODO also aggregate some pca outputs + linearity analysis outputs,
# so that down here i can do stuff like compare # of cells superlinear / or at
# least compare fits

#plt.show()
import ipdb; ipdb.set_trace()


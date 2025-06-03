import warnings
import numpy as np
import scipy as sp
from scipy import cluster as scl
from nilearn import input_data as nid
from sklearn import linear_model as sln
from sklearn import preprocessing as skp


def pearson_r(data, pheno, covariate_name):
    # Remove missing values
    mask = ~pheno[covariate_name].isnull().values
    covariate = pheno[covariate_name]
    contrast_name = f'Pearson_r with {covariate_name}'
    r, p = sp.stats.pearsonr(data[mask], covariate[mask])
    result = {'pearson_r': r,
              'p': p,
              'contrast': contrast_name}
    return result


def t_test(data, pheno, group, case, control):
    # We cannot assume that the index is reset or consecutive from 0,
    # Let's instead get the precise position
    case_idx = np.array([pheno.index.get_loc(idx) for idx in pheno.query(f'{group} == "{case}"').index.values])
    control_idx = np.array([pheno.index.get_loc(idx) for idx in pheno.query(f'{group} == "{control}"').index.values])
    contrast_name = f'T_Test     of {group}: {case} vs {control}'

    n_case = len(case_idx)
    n_control = len(control_idx)
    t, p = sp.stats.ttest_ind(data[case_idx], data[control_idx])
    mean_case = np.mean(data[case_idx])
    mean_control = np.mean(data[control_idx])
    pooled_std = np.sqrt((((n_case - 1) * np.square(np.std(data[case_idx]))) +
                         ((n_control - 1) * np.square(np.std(data[case_idx])))) / (n_case + n_control - 2))
    cohens = (mean_case - mean_control) / pooled_std
    results = {'t': t,
               'p': p,
               'cohens_d': cohens,
               'mean_case': mean_case,
               'mean_control': mean_control,
               'contrast': contrast_name,
               'pooled_sd': pooled_std}
    return results


def corr2_coeff(A, B):
    # Rowwise mean of input arrays & subtract from input arrays themeselves
    A_mA = A - A.mean(1)[:, None]
    B_mB = B - B.mean(1)[:, None]

    # Sum of squares across rows
    ssA = (A_mA ** 2).sum(1)
    ssB = (B_mB ** 2).sum(1)

    # Finally get corr coeff
    return np.dot(A_mA, B_mB.T) / np.sqrt(np.dot(ssA[:, None], ssB[None]))


def seed_correlation(functional_image, atlas_image, mask_image):
    """

    :param functional_image: 4D nibabel image with time in the 4th dimension
    :param atlas_image: 3D nibabel image with integers for ROIs and 0 as background
    :param mask_image: 3D nibabel image with 0 as background and 1 as brain.
    :return: fisher z transformed correlations. shape = (n_voxels, n_regions)
    """
    atlas_masker = nid.NiftiLabelsMasker(labels_img=atlas_image, mask_img=mask_image, standardize=True)
    brain_masker = nid.NiftiMasker(mask_image, verbose=0, standardize=True)
    seed_time_series = atlas_masker.fit_transform(functional_image)
    brain_time_series = brain_masker.fit_transform(functional_image)

    seed_correlations = np.dot(brain_time_series.T, seed_time_series) / seed_time_series.shape[0]
    seed_correlations_fisher_z = np.arctanh(seed_correlations)

    # seed_based_correlation_img = brain_masker.inverse_transform(seed_correlations_fisher_z.T)
    return seed_correlations_fisher_z


def nuisance_correction(data_stack, design_matrix, n_jobs=1):
    """
    :param data_stack: 2D or 3D array of (n_subjects, n_voxels, n_seeds)
    :param design_matrix: patsy or numpy style design matrix (n_subjects, n_factors)
    :param n_jobs:
    :return: residuals as 2D or 3D array of same dimensions as input array
    """
    model = sln.LinearRegression(fit_intercept=False, normalize=False, n_jobs=n_jobs)
    if data_stack.ndim == 3:
        n_seeds = data_stack.shape[2]
        residuals = np.stack([nuisance_correction(data_stack[..., seed_id], design_matrix, n_jobs)
                              for seed_id in range(n_seeds)], -1)
    else:
        results = model.fit(design_matrix, data_stack)
        residuals = data_stack - results.predict(design_matrix)

    return residuals


def subtype_maps(data_stack, part, method=np.mean):
    """

    :param data_stack: (n_subject, n_voxel, n_seed (optional)). 2D or 3D array of the data
    :param part: (n_subject, n_seed (optional) 1D or 2D array of subtype partitions. Zero values are ignored to allow
                 for thresholded subtypes
    :param method: A function reference to compute the subtype map. Default is numpy.mean
    :return: numpy array for 2D input and list of numpy arrays for 3D input
    """
    if data_stack.ndim == 3 or part.ndim == 2:
        if not (data_stack.ndim == 3 and part.ndim == 2) or not data_stack.shape[-1] == part.shape[-1]:
            raise Exception(f'data and part must have the same last dimension when run across seeds: '
                            f'data({data_stack.shape}), part({part.shape})')
        n_iter = part.shape[-1]
        sbt_maps = [subtype_maps(data_stack[..., i], part[..., i]) for i in range(n_iter)]
    else:
        n_subtypes = np.sum(np.unique(part) != 0)
        sbt_maps = np.array([method(data_stack[part == sbt_id, :], 0) for sbt_id in range(1, n_subtypes + 1)])
    return sbt_maps


def constrain_partition(partition, min_cases=2):
    """

    :param partition: 1D partition vector where each unique number corresponds to a part
    :param min_cases: the minimum number of occurrences for a part to be kept in the constrained partition
    :return:
    """
    masked_partition = np.array([0 if sum(partition == p) < min_cases else p for p in partition])
    # The remaining elements will always be sorted so 0 can remain 0
    remaining_elements = list(np.unique(masked_partition))
    if 0 in remaining_elements:
        # Reassign values to the remaining partitions
        constrained_partition = np.array([remaining_elements.index(p) for p in masked_partition])
    else:
        # Nothing to do, all elements of the partition are more frequent than required
        constrained_partition = masked_partition

    return constrained_partition


def subtype_partition(data_stack, mode='classic', n_subtypes=3, dist_thr=0.7, part_thr=20):
    """

    :param data_stack: 2D or 3D array (n_subjects, n_connections, n_seeds) (last optional)
    :param n_subtypes: int
    :param mode: str. Either 'classic' for regular subtypes, 'core' for thresholded subtypes, or 'relative' to have the
                      thresholds interpreted as rank percentages.
    :param dist_thr: float. Thresholds clusters by cophenetic distance
    :param part_thr: int. Only keep parts that have at least this many occurrences.
    :return:
    """
    if data_stack.ndim == 3:
        # Process recursively and stack the results along the last (new) dimension
        n_iter = data_stack.shape[2]
        part, dist, order = list(map(lambda x: np.stack(x, -1),
                                     zip(*[subtype_partition(data_stack[..., i], mode, n_subtypes, dist_thr, part_thr)
                                           for i in range(n_iter)])))
    else:
        if mode == 'classic':
            # Normalize to 0 mean and unit variance across voxels per subject
            norm = skp.scale(data_stack, axis=1)
            # Get the lower triangle of the distance metric
            dist = sp.spatial.distance.pdist(norm)
            # Build the cluster
            link = scl.hierarchy.linkage(dist, method='ward', optimal_ordering=True)
            order = scl.hierarchy.dendrogram(link, no_plot=True)['leaves']
            part = scl.hierarchy.fcluster(link, n_subtypes, criterion='maxclust')
        elif mode == 'core':
            sim = np.corrcoef(data_stack)
            dist = 1 - sim[np.triu(np.ones(shape=sim.shape), 1).astype(bool)]
            link = scl.hierarchy.linkage(dist, method='average', optimal_ordering=True)
            order = scl.hierarchy.dendrogram(link, no_plot=True)['leaves']
            full_partition = scl.hierarchy.fcluster(link, dist_thr, criterion='distance')
            part = constrain_partition(full_partition, min_cases=part_thr)
            if np.max(part) == 0:
                warnings.warn(f'Cannot find any subtypes that satisfy the criteria! Partition is empty.\n'
                              f'    Subtyping {data_stack.shape[0]} cases in {mode} mode with a distance cutoff of '
                              f'{dist_thr} and a minimum number of cases per subtype of {part_thr} ')
        elif mode == 'relative':
            sim = np.corrcoef(data_stack)
            n_subject = sim.shape[0]
            part_thr_emp = np.ceil(n_subject * part_thr).astype(int)
            dist = 1 - sim[np.triu(np.ones(shape=sim.shape), 1).astype(bool)]
            dist_thr_emp = np.percentile(dist, dist_thr)
            link = scl.hierarchy.linkage(dist, method='average', optimal_ordering=True)
            order = scl.hierarchy.dendrogram(link, no_plot=True)['leaves']
            full_partition = scl.hierarchy.fcluster(link, dist_thr_emp, criterion='distance')
            part = constrain_partition(full_partition, min_cases=part_thr_emp)
            if np.max(part) == 0:
                warnings.warn(f'Cannot find any subtypes that satisfy the criteria! Partition is empty.\n'
                              f'    Subtyping {data_stack.shape[0]} cases in {mode} mode with a distance cutoff of '
                              f'{dist_thr_emp } and a minimum number of cases per subtype of {part_thr_emp} ')
        else:
            raise Exception(f'{mode} is not implemented as mode to generate subtypes. Please use "classic" or "core".')

    return part, dist, order


def subtype_weights(data_stack, subtypes):
    """

    :param subtypes: 2D array of shape (n_subtype, n_voxel) or a list of 2D arrays, one for each seed region
    :param data_stack: 2D or 3D array of shape (n_subjects, n_voxel, n_seeds) - last optional
    :return: weight matrix as 2D or 3D array with shape (n_subjects, n_subtypes, n_seeds) - last optional
    """
    if not type(subtypes) == list:
        if subtypes.size == 0:
            warnings.warn(f'I encountered an empty subtype map. This can happen if the corresponding partition that '
                          f'generated this subtypes was thresholded until there were no individuals in a subtype '
                          f'left. I will not crash here but I will return all NaN weights. Goodbye.')
            # I will create all-zero weights if the subtype map is an empty array (indicating that this is a seed
            # without any satisfactory subtypes
            weights = np.empty(shape=(data_stack.shape[0], 1))
            weights[:] = np.nan

        elif not subtypes.ndim == 2 or not data_stack.ndim == 2:
            raise Exception(f'subtypes and data must have the same dimensions: '
                            f'subtypes ({subtypes.ndim}; {type(subtypes)}) '
                            f'data ({data_stack.ndim}; {type(data_stack)})')

        else:
            weights = corr2_coeff(data_stack, subtypes)
    else:
        if not len(subtypes) == data_stack.shape[2]:
            raise Exception(f'Data is 3D but the number of seed regions is mismatched between subtypes and data: '
                            f'subtype ({len(subtypes)}) and data ({data_stack.shape[2]})')
        n_seeds = len(subtypes)
        weights = [subtype_weights(data_stack[..., seed_id], subtypes[seed_id]) for seed_id in range(n_seeds)]
    return weights


def compute_icc(ratings, cse, kind):
    """
    Computes the interclass correlations for indexing the reliability analysis
    according to shrout & fleiss' schema.

    ratings - ratings data matrix, data whose rows represent different
        ratings/raters & whose columns represent different cases or
        targets being measured. Each target is assumed too be a random
        sample from a population of targets.
    cse - 1 2 or 3: 1 if each target is measured by a different set of
        raters from a population of raters, 2 if each target is measured
        by the same raters, but that these raters are sampled from a
        population of raters, 3 if each target is measured by the same
        raters and these raters are the only raters of interest.
   kind - 'single' or 'k': denotes whether the ICC is based on a single
        measurement or on an average of k measurements, where
        k = the number of ratings/raters.

        % REFERENCE:
%   Shrout PE, Fleiss JL. Intraclass correlations: uses in assessing rater
%   reliability. Psychol Bull. 1979;86:420-428
%
% NOTE:
%   This code was mainly modified with the Kevin's codes in web.
%   (London kevin.brownhill@kcl.ac.uk)
%
% XINIAN ZUO
% Email: zuoxinian@gmail.com

% if isanova
%     [p,table,stats] = anova1(x',{},'off');
%     ICC=(table{2,4}-table{3,4})/(table{2,4}+table{3,3}/(table{2,3}+1)*table{3,4});
% else
    """

    # k is the number of raters, and n is the number of targets
    k, n = ratings.shape
    # mean per target
    mpt = np.mean(ratings, 0)
    # mean per rater
    mpr = np.mean(ratings, 1)
    # get total mean
    tm = np.mean(ratings)
    # within target sum sqares
    wss = np.sum(np.square(ratings - mpt))
    # within target mean sqares
    wms = wss / (n * (k - 1))
    # between rater sum squares
    rss = np.sum(np.square(mpr - tm)) * n
    # between rater mean squares
    rms = rss / (k - 1)
    # between target sum squares
    bss = np.sum(np.square(mpt - tm)) * k
    # between target mean squares
    bms = bss / (n - 1)
    # residual sum of squares
    ess = wss - rss
    # residual mean squares
    ems = ess / ((k - 1) * (n - 1))

    if cse == 1:
        if kind == 'single':
            icc = (bms - wms) / (bms + (k - 1) * wms)
        elif kind == 'k':
            icc = (bms - wms) / bms
        else:
            raise Exception(f'Wrong value for "kind": {kind}')
    elif cse == 2:
        if kind == 'single':
            icc = (bms - ems) / (bms + (k - 1) * ems + k * (rms - ems) / n)
        elif kind == 'k':
            icc = (bms - ems) / (bms + (rms - ems) / n)
        else:
            raise Exception(f'Wrong value for "kind": {kind}')
    elif cse == 3:
        if kind == 'single':
            icc = (bms - ems) / (bms + (k - 1) * ems)
        elif kind == 'k':
            icc = (bms - ems) / bms
        else:
            raise Exception(f'Wrong value for "kind": {kind}')
    else:
        raise Exception('Wrong value for "cse": {cse}')
    return icc, wms, bms

import functools
import numpy as np
import nibabel as nib
import pathlib as pal
from .stats import seed_correlation, \
    subtype_partition, subtype_maps, subtype_weights, \
    compute_icc


def unpacker(func):
    # Wrapper used to turn argument functions into parallelizable functions that accept just one argument
    @functools.wraps(func)
    def wrapper_unpacker(arg_dict):
        return func(**arg_dict)
    return wrapper_unpacker


def wrap_seed_based_correlation(func_in_p, sca_out_p, atlas_img, mask_img, confound_img=None, clobber=False):
    """

    :param func_in_p: path to scrubbed functional time series
    :param sca_out_p: pathlib path to .npy file that will contain the seed maps
    :param atlas_img: nibabel image of atlas partition
    :param mask_img: nibabel image of atlas mask
    :param confound_img: nibabel image of confounds to be regressed. Uses partial seed correlation.
                         None if none are to be regressed
    :param clobber: if True, overwrite. Otherwise stop if output exists
    :return:
    """
    if not issubclass(type(sca_out_p), pal.Path):
        sca_out_p = pal.Path(sca_out_p)
    if sca_out_p.is_file() and not clobber:
        raise Exception(f'Designated output file exists. Set clobber=True to overwrite:\n{sca_out_p}')
    func_i = nib.load(str(func_in_p))
    seed_map_fisher_z = seed_correlation(func_i, atlas_img, mask_img)
    np.save(str(sca_out_p), seed_map_fisher_z)
    return sca_out_p.is_file()


def wrap_weight_stability(data_stack, sbt_ids, icc_ids, mode='classic', n_subtypes=3, dist_thr=0.7, part_thr=20):
    """
    type: (np.ndarray, tuple, tuple, str, int, float, int) -> np.ndarray

    :param data_stack: numpy.ndarray of 4D
    :param sbt_ids: tuple with integer indices of the session to be used to generate subtypes
    :param icc_ids: tuple with integer indices of the sessions used to compute ICC on weights
    :param mode: str. Can be 'classic' for fixed subtypes or 'core' for data dependent subtypes based on thresholds
    :param n_subtypes: (only in 'classic' mode)
    :param dist_thr: (only in 'core' mode) float. maximum distance of subjects in a subtype
    :param part_thr: (only in 'core' mode) int, minimum number of subjects that need to be in a valid subtype
    :return:
    """
    if not data_stack.ndim == 4:
        raise Exception(f'Data Stack must be 4D array but has shape {data_stack.shape} ({data_stack.ndim} D)')

    scale = data_stack.shape[2]
    n_icc = len(icc_ids)
    # Average the sessions used to make subtypes
    sbt_stack = np.mean(data_stack[..., sbt_ids], -1)
    # Slice the sessions used for the weights
    icc_stack = data_stack[..., icc_ids]
    # Transitioned this to thresholded subtype mode
    partition, distance, _ = subtype_partition(sbt_stack, mode=mode, n_subtypes=n_subtypes,
                                               dist_thr=dist_thr, part_thr=part_thr)
    subtypes = subtype_maps(sbt_stack, partition)
    weight_list = [subtype_weights(icc_stack[..., w_id], subtypes) for w_id in range(n_icc)]

    # The weight list is ordered: [ sessions [ seeds (subjects, subtype) ] ] with the tuple being the weights
    # Because the number of subtypes can differ between seeds, we cannot store this as an array
    # Instead we unpack the list. One advantage here is that the number of subtypes is the same for all the icc session
    # for which we extract the weights. So we can just pick one of the icc sessions and check the shape of the weights.
    # Then we iterate over the number of subtypes we found to get an intermediate list if subtypes with each element
    # having the shape of (n_subject, n_session) ]. Then we end up with a (n_subtype, 3 - for the 3 returns) array
    # which we average across subtypes to receive a 3-tuple of (icc, wms, bms). We iterate over seeds and stack those
    # tuples up which means that at the end we arrive at a (n_seeds, 3) array. This wouldn't really work without
    # averaging across subtypes.
    results = np.array([np.mean(np.stack([compute_icc(np.stack([weight_list[ses][seed][:, sbt]
                                                                for ses in range(n_icc)], -1).T, 1, 'single')
                                          for sbt in range(weight_list[0][seed].shape[1])], axis=-1), axis=1)
                        for seed in range(scale)])
    n_sbt = list()
    avg_size_sbt = list()
    min_size_sbt = list()
    n_in_sbt = list()
    n_out_sbt = list()
    for seed_id in range(scale):
        n_sbt.append(np.max(partition[:, seed_id]))
        n_in_sbt.append(np.sum(partition[:, seed_id] != 0))
        n_out_sbt.append(np.sum(partition[:, seed_id] == 0))
        if np.max(partition[:, seed_id]) == 0:
            avg_size_sbt.append(0)
            min_size_sbt.append(0)
        else:
            avgsz = np.mean([np.sum(partition[:, seed_id] == part_id)
                             for part_id in np.unique(partition[:, seed_id]) if not part_id == 0])
            minsz = np.min([np.sum(partition[:, seed_id] == part_id)
                            for part_id in np.unique(partition[:, seed_id]) if not part_id == 0])
            avg_size_sbt.append(avgsz)
            min_size_sbt.append(minsz)

    sbt_info = np.stack([n_sbt, n_in_sbt, n_out_sbt, avg_size_sbt, min_size_sbt], -1)
    res_array = np.concatenate([results, sbt_info], 1)
    # The res_array has the dimensions (n_seeds, 8. With the following order
    # icc, wms, bms, n_sbt, n_subjects_in_subtypes, n_subjects_outside_subtypes, avg_subtype_size, min_subtype_size
    return res_array

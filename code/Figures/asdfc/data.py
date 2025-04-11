import warnings
import nibabel as nib
import pathlib as pal
from scipy import io as sio


def niak_scrubbing(img_p, extra_p, out_p, clobber=False):
    """

    :param img_p: pathlib path to the functional image file
    :param extra_p: pathlib path to the .mat file that contains the scrubbing mask
    :param out_p: pathlib path to the output functional image file
    :param clobber: if true, overwrite existing output image file
    :return:
    """
    if not issubclass(type(out_p), pal.Path):
        out_p = pal.Path(out_p)

    if out_p.is_file() and not clobber:
        warnings.warn(f'{out_p.name} already exists and clobber = {clobber}. Not touching anything:\n {out_p}')
        return out_p.is_file()

    img = nib.load(str(img_p))
    extra = sio.loadmat(str(extra_p))

    scrub_mask = extra['mask_scrubbing'].squeeze()
    # Check that the length of the mask matches that of the temporal dimension
    if not len(scrub_mask) == img.shape[-1]:
        raise Exception(f'Shape mismatch between {img_p.name} and {extra_p.name}: {img.shape} vs {len(scrub_mask)}')

    masked_img = nib.Nifti1Image(img.get_data()[..., scrub_mask != 1], affine=img.affine, header=img.header)
    nib.save(masked_img, str(out_p))
    return out_p.is_file()

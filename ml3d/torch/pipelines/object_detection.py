import torch
import logging
from tqdm import tqdm

from datetime import datetime

from os.path import exists, join

from .base_pipeline import BasePipeline
from ..dataloaders import TorchDataloader
from ..utils import latest_torch_ckpt
from ...utils import make_dir, PIPELINE, LogRecord

logging.setLogRecordFactory(LogRecord)
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(asctime)s - %(module)s - %(message)s',
)
log = logging.getLogger(__name__)


class ObjectDetection(BasePipeline):
    """
    Pipeline for object detection. 
    """

    def __init__(self,
                 model,
                 dataset=None,
                 name='ObjectDetection',
                 main_log_dir='./logs/',
                 device='gpu',
                 split='train',
                 **kwargs):
        super().__init__(model=model,
                         dataset=dataset,
                         name=name,
                         main_log_dir=main_log_dir,
                         device=device,
                         split=split,
                         **kwargs)

    def run_inference(self, data):
        """
        Run inference on a given data.

        Args:
            data: A raw data.
        Returns:
            Returns the inference results.
        """
        model = self.model
        device = self.device

        model.to(device)
        model.device = device
        model.eval()

        with torch.no_grad():
            inputs = torch.tensor([data['point']],
                                  dtype=torch.float32,
                                  device=self.device)
            results = model(inputs)
            boxes = model.inference_end(results)

        return boxes

    def run_test(self):
        model = self.model
        dataset = self.dataset
        device = self.device
        cfg = self.cfg
        model.device = device
        model.to(device)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')

        log.info("DEVICE : {}".format(device))
        log_file_path = join(cfg.logs_dir, 'log_test_' + timestamp + '.txt')
        log.info("Logging in file : {}".format(log_file_path))
        log.addHandler(logging.FileHandler(log_file_path))

        test_split = TorchDataloader(dataset=dataset.get_split('test'),
                                     preprocess=model.preprocess,
                                     transform=model.transform,
                                     use_cache=dataset.cfg.use_cache,
                                     shuffle=False)

        self.load_ckpt(model.cfg.ckpt_path)

        log.info("Started testing")

        results = []
        with torch.no_grad():
            for idx in tqdm(range(len(test_split)), desc='test'):
                data = test_split[idx]
                result = self.run_inference(data['data'])
                results.extend(result)

    def run_train(self):
        raise NotImplementedError()

    def load_ckpt(self, ckpt_path=None, is_resume=True):
        checkpoint = torch.load(ckpt_path, map_location=self.device)

        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint

        if list(state_dict.keys())[0].startswith('module.'):
            state_dict = {k[7:]: v for k, v in checkpoint['state_dict'].items()}

        self.model.load_state_dict(state_dict)


PIPELINE._register_module(ObjectDetection, "torch")

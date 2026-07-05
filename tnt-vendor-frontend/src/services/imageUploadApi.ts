import apiClient from './apiClient';

export interface UploadResponse {
  url: string;
  filename: string;
  size: number;
  content_type: string;
}

export const imageUploadApi = {
  uploadLogo: async (imageUri: string, onProgress?: (progress: number) => void): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', {
      uri: imageUri,
      type: 'image/jpeg',
      name: 'logo.jpg',
    } as any);

    return apiClient.post(`/v1/vendors/profile/upload/logo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    }).then(res => res.data);
  },

  uploadCoverImage: async (imageUri: string, onProgress?: (progress: number) => void): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', {
      uri: imageUri,
      type: 'image/jpeg',
      name: 'cover.jpg',
    } as any);

    return apiClient.post(`/v1/vendors/profile/upload/cover`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    }).then(res => res.data);
  },

  deleteImage: async (imageType: 'logo' | 'cover'): Promise<void> => {
    await apiClient.delete(`/v1/vendors/profile/upload/${imageType}`);
  },
};

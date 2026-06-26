// Image Compression Utility

export interface CompressionOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
  format?: 'jpeg' | 'png' | 'webp';
}

export const DEFAULT_OPTIONS: CompressionOptions = {
  maxWidth: 1024,
  maxHeight: 1024,
  quality: 0.8,
  format: 'jpeg',
};

/**
 * Compress image file
 * Note: In React Native, actual compression happens during image picker
 * This utility provides configuration and validation
 */
export async function compressImage(
  imageUri: string,
  options: CompressionOptions = {}
): Promise<{ uri: string; size: number; width: number; height: number }> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  try {
    // In a real implementation, you would use:
    // - react-native-image-crop-picker for cropping/compression
    // - react-native-image-resizer for resizing
    // - expo-image-manipulator (if using Expo)

    // For now, return the original URI with metadata
    // The actual compression is handled by the image picker
    
    return {
      uri: imageUri,
      size: 0, // Would be calculated from actual file
      width: opts.maxWidth || 1024,
      height: opts.maxHeight || 1024,
    };
  } catch (error) {
    console.error('Image compression failed:', error);
    throw new Error('Failed to compress image');
  }
}

/**
 * Validate image file
 */
export function validateImage(file: {
  uri: string;
  size?: number;
  type?: string;
}): { valid: boolean; error?: string } {
  // Check file size (max 5MB)
  const maxSize = 5 * 1024 * 1024; // 5MB
  if (file.size && file.size > maxSize) {
    return {
      valid: false,
      error: 'Image size must be less than 5MB',
    };
  }

  // Check file type
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (file.type && !validTypes.includes(file.type)) {
    return {
      valid: false,
      error: 'Invalid image format. Use JPEG, PNG, or WebP',
    };
  }

  // Check file extension
  const validExtensions = ['.jpg', '.jpeg', '.png', '.webp'];
  const extension = file.uri.toLowerCase().split('.').pop();
  if (extension && !validExtensions.includes(`.${extension}`)) {
    return {
      valid: false,
      error: 'Invalid file extension',
    };
  }

  return { valid: true };
}

/**
 * Get image dimensions
 */
export async function getImageDimensions(
  imageUri: string
): Promise<{ width: number; height: number }> {
  // In a real implementation, use:
  // - Image.getSize() from react-native
  // - Or expo-image-manipulator
  
  return {
    width: 1024,
    height: 1024,
  };
}

/**
 * Calculate aspect ratio
 */
export function calculateAspectRatio(width: number, height: number): number {
  return width / height;
}

/**
 * Generate thumbnail
 */
export async function generateThumbnail(
  imageUri: string,
  size: number = 150
): Promise<string> {
  // In a real implementation, use:
  // - react-native-image-crop-picker
  // - Or custom thumbnail generation
  
  return imageUri;
}